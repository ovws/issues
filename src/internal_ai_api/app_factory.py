from __future__ import annotations

import asyncio
import json
import re
import time
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from .auth import require_api_key
from .config import Settings
from .db import Database
from .logging_utils import configure_logging
from .maintenance import cleanup_loop
from .proxy import ProxyResult, UpstreamProxy
from .queue import FifoQueue, QueueFullError
from .request_ids import request_id
from .video_bridge import (
    VIDEO_MODEL,
    VideoChatRequest,
    parse_video_chat_request,
    parse_video_responses_request,
    video_payload,
    video_response,
)


def openai_error(status_code: int, message: str, error_type: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type, "code": None}},
    )


def create_proxy_app(settings: Settings) -> FastAPI:
    logger = configure_logging(settings.log_dir, settings.platform)
    started_at = time.monotonic()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(settings.db_path)
        queue = FifoQueue(database, settings.platform, settings.queue_capacity, logger)
        client = httpx.AsyncClient(timeout=None, follow_redirects=True)
        app.state.database = database
        app.state.queue = queue
        app.state.proxy = UpstreamProxy(
            settings.upstream_url or "", settings.upstream_api_key or "", client
        )
        await queue.start()
        cleanup_task = asyncio.create_task(
            cleanup_loop(settings.media_dir, settings.retention_days, logger)
        )
        try:
            yield
        finally:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task
            await queue.stop()
            await client.aclose()

    app = FastAPI(
        title=settings.title,
        version="0.1.0",
        description=(
            "Company-LAN gateway. Upstream administration stays on loopback; "
            "generation calls use per-user keys and a single FIFO worker."
        ),
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request_id(request.headers.get("x-request-id"))
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_bytes:
                    return openai_error(413, "request body is too large", "request_too_large")
            except ValueError:
                return openai_error(400, "invalid Content-Length", "invalid_request")
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @app.get("/health", tags=["operations"])
    async def health(request: Request):
        return {
            "status": "ok",
            "platform": settings.platform,
            "uptime_seconds": round(time.monotonic() - started_at, 3),
            "queue": request.app.state.queue.health(),
            "jobs": request.app.state.database.counts(),
        }

    @app.api_route(
        "/v1/media/{media_path:path}",
        methods=["GET", "HEAD", "PUT"],
        include_in_schema=False,
    )
    async def public_media(request: Request, media_path: str) -> Response:
        result = await request.app.state.proxy.forward(request, f"/v1/media/{media_path}")
        return result.response

    if settings.platform == "chatgpt-image":

        @app.api_route(
            "/images/{image_path:path}",
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
        async def public_chatgpt_image(request: Request, image_path: str) -> Response:
            result = await request.app.state.proxy.forward(request, f"/images/{image_path}")
            return result.response

    async def dispatch(request: Request, api_path: str, key_id: str) -> Response:
        path = f"/v1/{api_path}"
        if request.method == "POST" and path == "/v1/videos":
            path = "/v1/videos/generations"
        generation = request.method == "POST" and any(
            marker in path
            for marker in (
                "/chat/completions",
                "/responses",
                "/images/generations",
                "/images/edits",
                "/videos",
            )
        )
        if not generation:
            try:
                result = await request.app.state.proxy.forward(request, path)
                return result.response
            except httpx.HTTPError as exc:
                logger.warning(
                    "upstream_request_failed request_id=%s error=%s",
                    request.state.request_id,
                    exc,
                )
                return openai_error(502, "upstream service unavailable", "upstream_error")

        body = await request.body()
        if len(body) > settings.max_request_bytes:
            return openai_error(413, "request body is too large", "request_too_large")
        model = None
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                payload = json.loads(body)
                model = payload.get("model") if isinstance(payload, dict) else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        spool_path = None
        inline_body: bytes | None = body
        if len(body) > 1024 * 1024:
            spool_dir = settings.media_dir / ".requests"
            spool_dir.mkdir(parents=True, exist_ok=True)
            spool_path = spool_dir / f"{request.state.request_id}.body"
            await asyncio.to_thread(spool_path.write_bytes, body)
            inline_body = None
            body = b""

        async def operation():
            try:
                request_body = inline_body
                if spool_path:
                    request_body = await asyncio.to_thread(spool_path.read_bytes)
                return await request.app.state.proxy.forward(request, path, request_body)
            finally:
                if spool_path:
                    spool_path.unlink(missing_ok=True)

        try:
            result = await request.app.state.queue.submit(
                endpoint=path,
                model=model,
                request_id=request.state.request_id,
                key_id=key_id,
                timeout=settings.timeouts.for_path(path),
                operation=operation,
            )
            return result.response
        except QueueFullError:
            if spool_path:
                spool_path.unlink(missing_ok=True)
            return openai_error(429, "platform FIFO queue is full", "queue_full")
        except TimeoutError:
            return openai_error(504, "generation timed out and was not retried", "timeout")
        except httpx.HTTPError:
            return openai_error(502, "upstream service unavailable", "upstream_error")
        except Exception as exc:
            logger.exception("gateway_error request_id=%s error=%s", request.state.request_id, exc)
            raise HTTPException(status_code=502, detail="upstream request failed") from exc

    async def video_client_bridge(
        request: Request, key_id: str, video_request: VideoChatRequest
    ) -> Response:
        if not video_request.image_url:
            return video_response(
                video_request,
                "连接成功。请在当前对话中上传一张图片，再输入希望图片如何运动。",
                response_id=(
                    "resp_video_ready"
                    if video_request.api_style == "responses"
                    else "chatcmpl-video-ready"
                ),
            )

        public_base = str(request.base_url).rstrip("/")

        async def operation() -> ProxyResult:
            proxy = request.app.state.proxy
            created = await proxy.request_json(
                "POST", "/v1/videos/generations", video_payload(video_request)
            )
            if created.status_code < 200 or created.status_code >= 300:
                return ProxyResult(
                    Response(
                        content=created.content,
                        status_code=created.status_code,
                        media_type=created.headers.get("content-type"),
                    )
                )
            created_payload = created.json()
            task_id = created_payload.get("request_id")
            if not isinstance(task_id, str) or not task_id:
                raise RuntimeError("video upstream did not return request_id")

            while True:
                await asyncio.sleep(2)
                status_response = await proxy.request_json("GET", f"/v1/videos/{task_id}")
                if status_response.status_code < 200 or status_response.status_code >= 300:
                    raise RuntimeError("video status query failed")
                status_payload = status_response.json()
                state = str(status_payload.get("status", "")).lower()
                if state in {"done", "completed", "succeeded"}:
                    video_url = f"{public_base}/v1/public/videos/{task_id}/content"
                    content = (
                        "视频生成完成。\n\n"
                        f"[点击播放或下载视频]({video_url})\n\n"
                        f"任务编号：`{task_id}`"
                    )
                    return ProxyResult(
                        video_response(
                            video_request,
                            content,
                            response_id=(
                                f"resp_{task_id}"
                                if video_request.api_style == "responses"
                                else f"chatcmpl-{task_id}"
                            ),
                        ),
                        result_location=task_id,
                    )
                if state in {"failed", "error", "cancelled", "canceled"}:
                    message = status_payload.get("error") or status_payload.get("error_message")
                    raise RuntimeError(f"video generation failed: {message or state}")

        try:
            result = await request.app.state.queue.submit(
                endpoint="/v1/videos/generations",
                model=VIDEO_MODEL,
                request_id=request.state.request_id,
                key_id=key_id,
                timeout=settings.timeouts.video,
                operation=operation,
            )
            return result.response
        except QueueFullError:
            return openai_error(429, "platform FIFO queue is full", "queue_full")
        except TimeoutError:
            return openai_error(504, "video generation timed out", "timeout")
        except Exception as exc:
            logger.exception(
                "video_client_bridge_failed request_id=%s error=%s",
                request.state.request_id,
                exc,
            )
            return openai_error(502, str(exc), "video_generation_failed")

    @app.get("/v1/models", tags=["OpenAI compatible"])
    async def models(request: Request, key_id: str = Depends(require_api_key)) -> Response:
        return await dispatch(request, "models", key_id)

    @app.post("/v1/chat/completions", tags=["OpenAI compatible"])
    async def chat_completions(
        request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        if settings.platform == "grok":
            video_request = parse_video_chat_request(await request.body())
            if video_request is not None:
                return await video_client_bridge(request, key_id, video_request)
        return await dispatch(request, "chat/completions", key_id)

    @app.post("/v1/responses", tags=["OpenAI compatible"])
    async def responses(request: Request, key_id: str = Depends(require_api_key)) -> Response:
        if settings.platform == "grok":
            video_request = parse_video_responses_request(await request.body())
            if video_request is not None:
                return await video_client_bridge(request, key_id, video_request)
        return await dispatch(request, "responses", key_id)

    @app.post("/v1/images/generations", tags=["OpenAI compatible"])
    async def image_generations(
        request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, "images/generations", key_id)

    @app.post("/v1/images/edits", tags=["OpenAI compatible"])
    async def image_edits(
        request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, "images/edits", key_id)

    @app.post(
        "/v1/videos",
        tags=["OpenAI compatible"],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["model", "image"],
                            "properties": {
                                "model": {
                                    "type": "string",
                                    "default": "grok-imagine-video-1.5",
                                },
                                "prompt": {"type": "string"},
                                "duration": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 15,
                                    "default": 5,
                                },
                                "aspect_ratio": {
                                    "type": "string",
                                    "enum": ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"],
                                    "default": "16:9",
                                },
                                "resolution": {
                                    "type": "string",
                                    "enum": ["480p", "720p", "1080p"],
                                    "default": "720p",
                                },
                                "image": {
                                    "type": "object",
                                    "required": ["url"],
                                    "properties": {"url": {"type": "string", "format": "uri"}},
                                },
                            },
                        },
                        "example": {
                            "model": "grok-imagine-video-1.5",
                            "prompt": "让画面中的主体自然运动，镜头平滑跟随，电影感",
                            "duration": 5,
                            "aspect_ratio": "16:9",
                            "resolution": "720p",
                            "image": {"url": "https://example.com/input.jpg"},
                        },
                    }
                },
            }
        },
    )
    async def create_video(
        request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, "videos", key_id)

    @app.get("/v1/videos/{task_id}", tags=["OpenAI compatible"])
    async def get_video(
        task_id: str, request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, f"videos/{task_id}", key_id)

    @app.get("/v1/videos/{task_id}/content", tags=["OpenAI compatible"])
    async def get_video_content(
        task_id: str, request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, f"videos/{task_id}/content", key_id)

    @app.get(
        "/v1/public/videos/{task_id}/content",
        tags=["OpenAI compatible"],
        include_in_schema=False,
    )
    async def public_video_content(task_id: str, request: Request) -> Response:
        if not re.fullmatch(r"video_[A-Za-z0-9_-]{10,100}", task_id):
            raise HTTPException(status_code=404, detail="video not found")
        return await request.app.state.proxy.stream_response(f"/v1/videos/{task_id}/content")

    @app.api_route(
        "/v1/{api_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    async def openai_proxy(
        request: Request, api_path: str, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, api_path, key_id)

    return app
