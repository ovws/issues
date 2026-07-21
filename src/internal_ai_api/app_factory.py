from __future__ import annotations

import asyncio
import html
import json
import time
from contextlib import asynccontextmanager, suppress
from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .auth import require_api_key
from .config import Settings
from .db import Database
from .logging_utils import configure_logging
from .maintenance import cleanup_loop
from .proxy import UpstreamProxy
from .queue import FifoQueue, QueueFullError
from .request_ids import request_id
from .video_chat import (
    GROK_VIDEO_CHAT_MODEL,
    GROK_VIDEO_UPSTREAM_MODEL,
    build_video_request,
    is_grok_video_chat_model,
    valid_video_access_token,
    video_access_token,
)


def openai_error(status_code: int, message: str, error_type: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type, "code": None}},
    )


class UpstreamTimeoutError(Exception):
    def __init__(self, retry_after: str | None = None):
        super().__init__("upstream origin timed out")
        self.retry_after = retry_after


def upstream_timeout_response(retry_after: str | None = None) -> JSONResponse:
    normalized = openai_error(
        504,
        "upstream origin timed out before completing the request; retry later",
        "timeout",
    )
    if retry_after:
        normalized.headers["retry-after"] = retry_after
    return normalized


def normalize_upstream_response(response: Response) -> Response:
    """Turn Cloudflare's HTML timeout page into an OpenAI-compatible error."""
    if response.status_code != 524:
        return response

    return upstream_timeout_response(response.headers.get("retry-after"))


def is_grok_video_model(model: object) -> bool:
    return isinstance(model, str) and "grok-imagine-video" in model.lower()


def adapt_grok_models_for_chat(response: Response) -> Response:
    """Replace raw video-only models with Cherry's chat-compatible video alias.

    OpenAI's ``/v1/models`` response has no standard capability field. Clients
    such as Cherry Studio therefore treat every returned model as a chat model
    and send it to ``/v1/chat/completions``. The alias contains ``vision`` so
    Cherry includes the previous assistant image in the last user message; the
    gateway then converts that chat request into the real video API workflow.
    """
    if response.status_code != 200 or not response.headers.get("content-type", "").startswith(
        "application/json"
    ):
        return response
    try:
        payload = json.loads(response.body)
    except (AttributeError, json.JSONDecodeError, UnicodeDecodeError):
        return response
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return response

    video_15 = next(
        (
            item
            for item in payload["data"]
            if isinstance(item, dict)
            and str(item.get("id", "")).lower() == GROK_VIDEO_UPSTREAM_MODEL
        ),
        None,
    )
    models = [
        item
        for item in payload["data"]
        if not isinstance(item, dict) or not is_grok_video_model(item.get("id"))
    ]
    if video_15:
        models.append(
            {
                **video_15,
                "id": GROK_VIDEO_CHAT_MODEL,
                "owned_by": "internal-video-compat",
            }
        )
    if models == payload["data"]:
        return response

    filtered_payload = {**payload, "data": models}
    headers = {
        name: value
        for name, value in response.headers.items()
        if name.lower() not in {"content-length", "transfer-encoding"}
    }
    return JSONResponse(status_code=response.status_code, content=filtered_payload, headers=headers)


def response_json(response: Response) -> dict[str, object] | None:
    try:
        payload = json.loads(response.body)
    except (AttributeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def video_result_text(public_url: str) -> str:
    safe_html_url = html.escape(public_url, quote=True)
    return (
        "✅ 视频已生成。\n\n"
        f'<video controls src="{safe_html_url}" style="max-width: 100%;"></video>\n\n'
        f"[打开或下载视频]({public_url})"
    )


def chat_completion(task_id: str, model: str, content: str) -> dict[str, object]:
    return {
        "id": f"chatcmpl-{task_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def chat_completion_chunk(
    task_id: str,
    model: str,
    *,
    content: str | None = None,
    role: str | None = None,
    finish_reason: str | None = None,
) -> bytes:
    delta: dict[str, str] = {}
    if role:
        delta["role"] = role
    if content is not None:
        delta["content"] = content
    payload = {
        "id": f"chatcmpl-{task_id}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n".encode()


def responses_usage() -> dict[str, object]:
    return {
        "input_tokens": 0,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens": 0,
        "output_tokens_details": {"reasoning_tokens": 0},
        "total_tokens": 0,
    }


def responses_completion(task_id: str, model: str, content: str) -> dict[str, object]:
    response_id = f"resp_{task_id}"
    item_id = f"msg_{task_id}"
    return {
        "id": response_id,
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": item_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": content,
                        "annotations": [],
                    }
                ],
            }
        ],
        "usage": responses_usage(),
    }


def responses_event(event_type: str, **values: object) -> bytes:
    payload = {"type": event_type, **values}
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_type}\ndata: {data}\n\n".encode()


def public_request_base(request: Request) -> str:
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        return f"{scheme}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


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

    async def fetch_video_status(request: Request, task_id: str) -> Response:
        result = await asyncio.wait_for(
            request.app.state.proxy.forward_as(
                request,
                "GET",
                f"/v1/videos/{quote(task_id, safe='')}",
            ),
            timeout=settings.timeouts.status,
        )
        return normalize_upstream_response(result.response)

    def status_error(payload: dict[str, object] | None, fallback: str) -> str:
        if payload:
            error = payload.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"]
        return fallback

    async def create_video_chat_compat(
        request: Request,
        payload: dict[str, object],
        key_id: str,
    ) -> Response:
        use_responses_api = request.url.path.rstrip("/") == "/v1/responses"
        try:
            video_payload = build_video_request(payload)
        except ValueError as exc:
            return openai_error(400, str(exc), "invalid_request")

        video_body = json.dumps(video_payload, ensure_ascii=False, separators=(",", ":")).encode()
        if len(video_body) > settings.max_request_bytes:
            return openai_error(413, "request body is too large", "request_too_large")

        async def create_operation():
            return await request.app.state.proxy.forward_as(
                request,
                "POST",
                "/v1/videos/generations",
                video_body,
            )

        try:
            created = await request.app.state.queue.submit(
                endpoint="/v1/videos/generations",
                model=GROK_VIDEO_UPSTREAM_MODEL,
                request_id=request.state.request_id,
                key_id=key_id,
                timeout=settings.timeouts.video,
                operation=create_operation,
            )
        except QueueFullError:
            return openai_error(429, "platform FIFO queue is full", "queue_full")
        except TimeoutError:
            return openai_error(504, "video task creation timed out", "timeout")
        except httpx.HTTPError:
            return openai_error(502, "upstream service unavailable", "upstream_error")

        created_response = normalize_upstream_response(created.response)
        if created_response.status_code < 200 or created_response.status_code >= 300:
            return created_response
        created_payload = response_json(created_response)
        task_id = created_payload.get("request_id") if created_payload else None
        if not isinstance(task_id, str) or not task_id:
            return openai_error(502, "video API did not return a request_id", "upstream_error")

        token = video_access_token(task_id, settings.upstream_api_key or "")
        public_url = (
            f"{public_request_base(request)}/v1/video-results/{quote(task_id, safe='')}/content"
            f"?token={token}"
        )
        model = str(payload.get("model") or GROK_VIDEO_CHAT_MODEL)
        deadline = time.monotonic() + settings.timeouts.video

        async def wait_for_result() -> tuple[dict[str, object] | None, Response | None]:
            consecutive_errors = 0
            while time.monotonic() < deadline:
                try:
                    status_response = await fetch_video_status(request, task_id)
                except (TimeoutError, httpx.HTTPError):
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        return None, None
                    await asyncio.sleep(5)
                    continue
                status_payload = response_json(status_response)
                if status_response.status_code >= 500:
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        return status_payload, status_response
                elif status_response.status_code >= 400:
                    return status_payload, status_response
                else:
                    consecutive_errors = 0
                    status = status_payload.get("status") if status_payload else None
                    if status in {"done", "failed"}:
                        return status_payload, status_response
                await asyncio.sleep(5)
            return None, None

        if not bool(payload.get("stream")):
            final_payload, final_response = await wait_for_result()
            if final_payload and final_payload.get("status") == "done":
                content = video_result_text(public_url)
                if use_responses_api:
                    return JSONResponse(responses_completion(task_id, model, content))
                return JSONResponse(chat_completion(task_id, model, content))
            if final_payload and final_payload.get("status") == "failed":
                return openai_error(
                    502,
                    status_error(final_payload, "video generation failed"),
                    "video_generation_failed",
                )
            if final_response and final_response.status_code >= 400:
                return final_response
            return openai_error(504, "video generation timed out", "timeout")

        async def stream_video_result():
            response_id = f"resp_{task_id}"
            item_id = f"msg_{task_id}"

            def text_chunk(content: str) -> bytes:
                if use_responses_api:
                    return responses_event(
                        "response.output_text.delta",
                        item_id=item_id,
                        output_index=0,
                        content_index=0,
                        delta=content,
                    )
                return chat_completion_chunk(task_id, model, content=content)

            if use_responses_api:
                yield responses_event(
                    "response.created",
                    response={
                        "id": response_id,
                        "object": "response",
                        "created_at": int(time.time()),
                        "status": "in_progress",
                        "model": model,
                    },
                )
                yield responses_event(
                    "response.output_item.added",
                    output_index=0,
                    item={
                        "id": item_id,
                        "type": "message",
                        "status": "in_progress",
                        "role": "assistant",
                        "content": [],
                    },
                )
            else:
                yield chat_completion_chunk(task_id, model, role="assistant", content="")
            yield text_chunk("🎬 视频任务已提交，正在生成，请稍候…")
            last_progress = -1
            consecutive_errors = 0
            while time.monotonic() < deadline:
                try:
                    status_response = await fetch_video_status(request, task_id)
                    status_payload = response_json(status_response)
                except (TimeoutError, httpx.HTTPError):
                    status_response = None
                    status_payload = None
                    consecutive_errors += 1
                else:
                    if status_response.status_code >= 500:
                        consecutive_errors += 1
                    elif status_response.status_code >= 400:
                        message = status_error(status_payload, "查询视频任务失败")
                        yield text_chunk(f"\n\n❌ {message}")
                        break
                    else:
                        consecutive_errors = 0
                        status = status_payload.get("status") if status_payload else None
                        if status == "done":
                            yield text_chunk(f"\n\n{video_result_text(public_url)}")
                            break
                        if status == "failed":
                            message = status_error(status_payload, "视频生成失败")
                            yield text_chunk(f"\n\n❌ {message}")
                            break
                        progress = status_payload.get("progress") if status_payload else None
                        if (
                            isinstance(progress, int)
                            and progress > 0
                            and progress >= last_progress + 10
                        ):
                            last_progress = progress
                            yield text_chunk(f"\n\n生成进度：{min(progress, 99)}%…")
                        else:
                            yield b": keep-alive\n\n"
                if consecutive_errors >= 3:
                    yield text_chunk("\n\n❌ 连续三次无法查询视频状态，请稍后重试。")
                    break
                await asyncio.sleep(5)
            else:
                yield text_chunk("\n\n❌ 视频生成等待超时，请稍后重试。")
            if use_responses_api:
                yield responses_event(
                    "response.output_item.done",
                    output_index=0,
                    item={
                        "id": item_id,
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [],
                    },
                )
                yield responses_event(
                    "response.completed",
                    response={
                        "id": response_id,
                        "object": "response",
                        "created_at": int(time.time()),
                        "status": "completed",
                        "model": model,
                        "usage": responses_usage(),
                    },
                )
            else:
                yield chat_completion_chunk(task_id, model, finish_reason="stop")
            yield b"data: [DONE]\n\n"

        return StreamingResponse(
            stream_video_result(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_started = time.perf_counter()
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
        logger.info(
            "http_request method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            round((time.perf_counter() - request_started) * 1000, 1),
            request.state.request_id,
        )
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

    @app.get("/v1/video-results/{task_id}/content", include_in_schema=False)
    async def public_video_result(request: Request, task_id: str) -> Response:
        token = request.query_params.get("token", "")
        if not valid_video_access_token(task_id, token, settings.upstream_api_key or ""):
            return openai_error(404, "video result not found", "not_found")
        try:
            result = await request.app.state.proxy.forward_as(
                request,
                "GET",
                f"/v1/videos/{quote(task_id, safe='')}/content",
            )
            return result.response
        except httpx.HTTPError:
            return openai_error(502, "upstream service unavailable", "upstream_error")

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
                response = normalize_upstream_response(result.response)
                if settings.platform == "grok" and path == "/v1/models":
                    response = adapt_grok_models_for_chat(response)
                return response
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
        payload = None
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                payload = json.loads(body)
                model = payload.get("model") if isinstance(payload, dict) else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        if (
            settings.platform == "grok"
            and path in {"/v1/chat/completions", "/v1/responses"}
            and is_grok_video_chat_model(model)
            and isinstance(payload, dict)
        ):
            return await create_video_chat_compat(request, payload, key_id)

        if (
            settings.platform == "grok"
            and is_grok_video_model(model)
            and path != "/v1/videos/generations"
        ):
            return openai_error(
                400,
                (
                    f"The model {model} is a video model and is only available on "
                    "POST /v1/videos (mapped to /v1/videos/generations)."
                ),
                "unsupported",
            )

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
                result = await request.app.state.proxy.forward(request, path, request_body)
                if result.response.status_code == 524:
                    raise UpstreamTimeoutError(result.response.headers.get("retry-after"))
                return result
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
            return normalize_upstream_response(result.response)
        except QueueFullError:
            if spool_path:
                spool_path.unlink(missing_ok=True)
            return openai_error(429, "platform FIFO queue is full", "queue_full")
        except UpstreamTimeoutError as exc:
            return upstream_timeout_response(exc.retry_after)
        except TimeoutError:
            return openai_error(504, "generation timed out and was not retried", "timeout")
        except httpx.HTTPError:
            return openai_error(502, "upstream service unavailable", "upstream_error")
        except Exception as exc:
            logger.exception("gateway_error request_id=%s error=%s", request.state.request_id, exc)
            raise HTTPException(status_code=502, detail="upstream request failed") from exc

    @app.get("/v1/models", tags=["OpenAI compatible"])
    async def models(request: Request, key_id: str = Depends(require_api_key)) -> Response:
        return await dispatch(request, "models", key_id)

    @app.post("/v1/chat/completions", tags=["OpenAI compatible"])
    async def chat_completions(
        request: Request, key_id: str = Depends(require_api_key)
    ) -> Response:
        return await dispatch(request, "chat/completions", key_id)

    @app.post("/v1/responses", tags=["OpenAI compatible"])
    async def responses(request: Request, key_id: str = Depends(require_api_key)) -> Response:
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

    @app.post("/v1/videos", tags=["OpenAI compatible"])
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
