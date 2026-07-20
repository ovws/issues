from __future__ import annotations

import asyncio
import hashlib
import json
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
from .proxy import UpstreamProxy
from .queue import FifoQueue, QueueFullError, QueuePausedError
from .request_ids import request_id
from .upstream_guard import (
    UpstreamFailureGuard,
    UpstreamResponseError,
    UpstreamTransportError,
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
        app.state.native_key_auth = settings.platform in {"grok", "chatgpt-image"}
        app.state.proxy = UpstreamProxy(
            settings.upstream_url or "",
            settings.upstream_api_key or "",
            client,
            forward_client_authorization=app.state.native_key_auth,
        )
        app.state.upstream_guard = UpstreamFailureGuard(
            settings.upstream_failure_threshold,
            immediate_pause_statuses=(
                frozenset() if app.state.native_key_auth else frozenset({401, 403, 429})
            ),
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
        queue_health = request.app.state.queue.health()
        return {
            "status": "paused" if queue_health["paused"] else "ok",
            "platform": settings.platform,
            "uptime_seconds": round(time.monotonic() - started_at, 3),
            "queue": queue_health,
            "jobs": request.app.state.database.counts(),
            "operator_action_required": bool(queue_health["paused"]),
        }

    @app.api_route(
        "/v1/media/{media_path:path}",
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
    async def public_media_read(request: Request, media_path: str) -> Response:
        result = await request.app.state.proxy.forward(request, f"/v1/media/{media_path}")
        return result.response

    @app.put("/v1/media/{media_path:path}", include_in_schema=False)
    async def authenticated_media_write(
        request: Request,
        media_path: str,
        key_id: str = Depends(require_api_key),
    ) -> Response:
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
        if request.app.state.queue.health()["paused"]:
            return openai_error(
                503,
                "platform generation is paused; operator action is required",
                "queue_paused",
            )
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
        async def forward_guarded(
            body: bytes | None = None, *, retry_safe: bool = False
        ):
            retries = settings.upstream_safe_retries if retry_safe else 0
            for attempt in range(retries + 1):
                guard = request.app.state.upstream_guard
                try:
                    result = await request.app.state.proxy.forward(request, path, body)
                except httpx.HTTPError as exc:
                    translated = guard.transport_failure(exc)
                    if attempt < retries:
                        delay = settings.upstream_retry_backoff_seconds * (2**attempt)
                        logger.warning(
                            "upstream_safe_retry request_id=%s attempt=%s delay=%ss error=%s",
                            request.state.request_id,
                            attempt + 1,
                            delay,
                            translated,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise translated from exc
                try:
                    return guard.inspect(result)
                except UpstreamResponseError as exc:
                    if exc.result.response.status_code >= 500 and attempt < retries:
                        delay = settings.upstream_retry_backoff_seconds * (2**attempt)
                        logger.warning(
                            "upstream_safe_retry request_id=%s attempt=%s delay=%ss error=%s",
                            request.state.request_id,
                            attempt + 1,
                            delay,
                            exc,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
            raise RuntimeError("unreachable retry state")

        if not generation:
            try:
                result = await forward_guarded(
                    retry_safe=request.method in {"GET", "HEAD"}
                )
                return result.response
            except UpstreamResponseError as exc:
                if exc.pause_queue:
                    request.app.state.queue.pause(exc.reason)
                return exc.result.response
            except UpstreamTransportError as exc:
                if exc.pause_queue:
                    request.app.state.queue.pause(exc)
                logger.warning(
                    "upstream_request_failed request_id=%s error=%s",
                    request.state.request_id,
                    exc,
                )
                return openai_error(502, "upstream service unavailable", "upstream_error")
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

        idempotency_key = request.headers.get("idempotency-key")
        if idempotency_key is not None:
            idempotency_key = idempotency_key.strip()
            if not idempotency_key or len(idempotency_key) > 200:
                return openai_error(
                    400,
                    "Idempotency-Key must contain 1 to 200 characters",
                    "invalid_request",
                )
        if path == "/v1/videos/generations" and not idempotency_key:
            return openai_error(
                400,
                "Idempotency-Key is required when creating a video task",
                "idempotency_key_required",
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
                return await forward_guarded(request_body)
            finally:
                if spool_path:
                    spool_path.unlink(missing_ok=True)

        try:
            queue_kwargs = {
                "endpoint": path,
                "model": model,
                "request_id": request.state.request_id,
                "key_id": key_id,
                "timeout": settings.timeouts.for_path(path),
                "operation": operation,
            }
            if idempotency_key:
                key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
                job_id, future, created = request.app.state.queue.enqueue_idempotent(
                    idempotency_key=key_hash,
                    **queue_kwargs,
                )
                if not created:
                    if spool_path:
                        spool_path.unlink(missing_ok=True)
                    existing = request.app.state.database.get_job(job_id)
                    if path == "/v1/videos/generations" and existing.get(
                        "result_location"
                    ):
                        response = JSONResponse(
                            status_code=200,
                            content={
                                "id": existing["result_location"],
                                "internal_job_id": job_id,
                                "idempotent_replay": True,
                            },
                        )
                    else:
                        response = openai_error(
                            409,
                            "this idempotent request was already submitted",
                            "duplicate_request",
                        )
                    response.headers["x-internal-job-id"] = job_id
                    response.headers["x-idempotent-replay"] = "true"
                    return response
                assert future is not None
            else:
                job_id, future = request.app.state.queue.enqueue(**queue_kwargs)
            result = await future
            result.response.headers["x-internal-job-id"] = job_id
            return result.response
        except QueueFullError:
            if spool_path:
                spool_path.unlink(missing_ok=True)
            return openai_error(429, "platform FIFO queue is full", "queue_full")
        except QueuePausedError:
            if spool_path:
                spool_path.unlink(missing_ok=True)
            return openai_error(
                503,
                "platform generation is paused; operator action is required",
                "queue_paused",
            )
        except UpstreamResponseError as exc:
            return exc.result.response
        except UpstreamTransportError:
            return openai_error(502, "upstream service unavailable", "upstream_error")
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
