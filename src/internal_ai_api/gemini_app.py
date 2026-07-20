from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .app_factory import openai_error
from .auth import require_api_key
from .config import load_settings
from .db import Database
from .gemini_backend import GeminiBackend, GeminiBackendError, MediaResult
from .gemini_multimodal import ChatInputError, prepare_chat_input
from .gemini_schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ImageGenerationRequest,
    ImageResponse,
    ModelList,
    VideoCreateRequest,
    VideoTaskResponse,
)
from .logging_utils import configure_logging
from .maintenance import cleanup_loop
from .queue import FifoQueue, QueueFullError, QueuePausedError
from .request_ids import request_id

settings = load_settings("gemini")
logger = configure_logging(settings.log_dir, settings.platform)
started_at = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = Database(settings.db_path)
    queue = FifoQueue(database, settings.platform, settings.queue_capacity, logger)
    backend = GeminiBackend(settings)
    app.state.database = database
    app.state.queue = queue
    app.state.backend = backend
    await queue.start()
    await backend.start()
    cleanup_task = asyncio.create_task(
        cleanup_loop(settings.media_dir, settings.retention_days, logger)
    )
    if backend.error:
        logger.warning("gemini_backend_degraded error=%s", backend.error)
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        await queue.stop()
        await backend.close()


app = FastAPI(
    title=settings.title,
    version="0.1.0",
    description="OpenAI-compatible layer for HanaokaYuzu/Gemini-API.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        if error["type"] in {"unsupported_content_type", "invalid_content_block"}:
            return openai_error(400, error["msg"], error["type"])
    details = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()[:3]
    )
    return openai_error(400, f"invalid request: {details}", "invalid_request")


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    codes = {
        401: "authentication_error",
        403: "permission_denied",
        404: "not_found",
        410: "content_expired",
    }
    response = openai_error(
        exc.status_code,
        str(exc.detail),
        codes.get(exc.status_code, "request_error"),
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


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
    backend = request.app.state.backend
    queue_health = request.app.state.queue.health()
    return {
        "status": "ok" if backend.client and not queue_health["paused"] else "degraded",
        "platform": settings.platform,
        "uptime_seconds": round(time.monotonic() - started_at, 3),
        "backend_error": backend.error,
        "account": backend.account_snapshot(),
        "queue": queue_health,
        "jobs": request.app.state.database.counts(),
    }


@app.get("/v1/models", tags=["OpenAI compatible"], response_model=ModelList)
async def list_models(request: Request, key_id: str = Depends(require_api_key)):
    try:
        return {"object": "list", "data": request.app.state.backend.models()}
    except GeminiBackendError as exc:
        return openai_error(exc.status_code, str(exc), exc.code)


async def queued(
    request: Request,
    key_id: str,
    endpoint: str,
    model: str | None,
    operation,
    on_rejected=None,
):
    try:
        return await request.app.state.queue.submit(
            endpoint=endpoint,
            model=model,
            request_id=request.state.request_id,
            key_id=key_id,
            timeout=settings.timeouts.for_path(endpoint),
            operation=operation,
        )
    except QueueFullError:
        if on_rejected:
            on_rejected()
        return openai_error(429, "platform FIFO queue is full", "queue_full")
    except QueuePausedError:
        if on_rejected:
            on_rejected()
        return openai_error(503, "platform FIFO queue is paused", "queue_paused")
    except TimeoutError:
        return openai_error(504, "generation timed out and was not retried", "timeout")
    except GeminiBackendError as exc:
        return openai_error(exc.status_code, str(exc), exc.code)
    except Exception as exc:
        logger.exception(
            "gemini_operation_failed request_id=%s error=%s",
            request.state.request_id,
            exc,
        )
        return openai_error(502, "Gemini upstream operation failed", "upstream_error")


async def stream_chat_result(result_task: asyncio.Task[Any]):
    try:
        while not result_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(result_task), timeout=10)
            except TimeoutError:
                yield ": keep-alive\n\n"
        result = result_task.result()
        if isinstance(result, MediaResult):
            result = result.payload
        if isinstance(result, JSONResponse):
            yield f"data: {result.body.decode('utf-8')}\n\n"
            yield "data: [DONE]\n\n"
            return

        choice = result["choices"][0]
        message = choice["message"]
        first_chunk = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": result["created"],
            "model": result["model"],
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": message["role"],
                        "content": message["content"],
                    },
                    "finish_reason": None,
                }
            ],
        }
        final_chunk = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": result["created"],
            "model": result["model"],
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(first_chunk, ensure_ascii=False, separators=(',', ':'))}\n\n"
        yield f"data: {json.dumps(final_chunk, ensure_ascii=False, separators=(',', ':'))}\n\n"
        yield "data: [DONE]\n\n"
    finally:
        if not result_task.done():
            result_task.cancel()


@app.post(
    "/v1/chat/completions",
    tags=["OpenAI compatible"],
    response_model=ChatCompletionResponse,
)
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    key_id: str = Depends(require_api_key),
):
    if payload.tools:
        return openai_error(400, "tools are not supported by this Gemini layer", "unsupported")
    model = payload.model or settings.gemini_default_model
    try:
        chat_input = await prepare_chat_input(
            payload.messages, settings, request.state.request_id
        )
    except ChatInputError as exc:
        return openai_error(exc.status_code, str(exc), exc.code)

    async def operation():
        try:
            output = await request.app.state.backend.generate(
                chat_input.prompt, model, files=chat_input.files
            )
            created = int(time.time())
            content = output.text or ""
            result_location = None
            images = list(output.images or [])
            if images:
                saved_images = await request.app.state.backend.save_images(
                    output,
                    "url",
                    min(len(images), 4),
                    str(request.base_url),
                )
                image_markdown = "\n\n".join(
                    f"![generated image {index}]({item['url']})"
                    for index, item in enumerate(saved_images.payload["data"], start=1)
                )
                content = "\n\n".join(part for part in (content, image_markdown) if part)
                result_location = saved_images.result_location
            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": created,
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
            return MediaResult(response, result_location) if result_location else response
        finally:
            chat_input.cleanup()

    async def submit():
        return await queued(
            request,
            key_id,
            "/v1/chat/completions",
            model,
            operation,
            on_rejected=chat_input.cleanup,
        )

    if payload.stream:
        result_task = asyncio.create_task(submit())
        return StreamingResponse(
            stream_chat_result(result_task),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    result = await submit()
    return result.payload if isinstance(result, MediaResult) else result


@app.post(
    "/v1/images/generations",
    tags=["OpenAI compatible"],
    response_model=ImageResponse,
)
async def image_generations(
    payload: ImageGenerationRequest,
    request: Request,
    key_id: str = Depends(require_api_key),
):
    model = payload.model or settings.gemini_default_model
    prompt = payload.prompt
    count = payload.n
    response_format = payload.response_format

    async def operation():
        output = await request.app.state.backend.generate(
            f"Generate an image. {prompt}", model
        )
        return await request.app.state.backend.save_images(
            output, response_format, count, str(request.base_url)
        )

    result = await queued(request, key_id, "/v1/images/generations", model, operation)
    return result.payload if hasattr(result, "payload") else result


@app.post(
    "/v1/images/edits",
    tags=["OpenAI compatible"],
    response_model=ImageResponse,
)
async def image_edits(
    request: Request,
    image: Annotated[list[UploadFile], File()],
    prompt: Annotated[str, Form()],
    model: Annotated[str, Form()] = "",
    n: Annotated[int, Form()] = 1,
    response_format: Annotated[str, Form()] = "url",
    key_id: str = Depends(require_api_key),
):
    selected_model = model or settings.gemini_default_model
    spool_dir = settings.media_dir / ".requests"
    spool_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    total_bytes = 0
    for index, upload in enumerate(image):
        path = spool_dir / f"{request.state.request_id}_{index}.upload"
        with path.open("wb") as destination:
            while chunk := await upload.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.max_request_bytes:
                    for temporary in [*files, path]:
                        temporary.unlink(missing_ok=True)
                    return openai_error(413, "uploaded images are too large", "request_too_large")
                destination.write(chunk)
        files.append(path)

    def cleanup_uploads():
        for temporary in files:
            temporary.unlink(missing_ok=True)

    async def operation():
        try:
            output = await request.app.state.backend.generate(
                f"Edit the attached image(s). {prompt}", selected_model, files=files
            )
            return await request.app.state.backend.save_images(
                output, response_format, max(1, min(n, 4)), str(request.base_url)
            )
        finally:
            cleanup_uploads()

    result = await queued(
        request,
        key_id,
        "/v1/images/edits",
        selected_model,
        operation,
        on_rejected=cleanup_uploads,
    )
    return result.payload if hasattr(result, "payload") else result


def _consume_future(future: asyncio.Future) -> None:
    if not future.cancelled():
        try:
            future.exception()
        except Exception:
            pass


def video_task_payload(job: dict[str, Any], *, replay: bool = False) -> dict[str, Any]:
    statuses = {
        "queued": "queued",
        "running": "in_progress",
        "succeeded": "completed",
        "failed": "failed",
        "timed_out": "failed",
        "interrupted": "failed",
    }
    return {
        "id": job["job_id"],
        "object": "video",
        "status": statuses.get(job["status"], "failed"),
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["finished_at"],
        "error": job["error"],
        "idempotent_replay": replay,
    }


@app.post(
    "/v1/videos",
    tags=["OpenAI compatible"],
    response_model=VideoTaskResponse,
    status_code=202,
)
async def create_video(
    payload: VideoCreateRequest,
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    key_id: str = Depends(require_api_key),
):
    model = payload.model or settings.gemini_video_model
    prompt = payload.prompt
    if idempotency_key and len(idempotency_key) > 200:
        return openai_error(400, "Idempotency-Key is too long", "invalid_request")

    async def operation():
        output = await request.app.state.backend.generate(
            f"Generate a video. {prompt}", model
        )
        return await request.app.state.backend.save_video(output)

    try:
        if idempotency_key:
            key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
            job_id, future, created = request.app.state.queue.enqueue_idempotent(
                endpoint="/v1/videos",
                model=model,
                request_id=request.state.request_id,
                key_id=key_id,
                idempotency_key=key_hash,
                timeout=settings.timeouts.video,
                operation=operation,
            )
        else:
            job_id, future = request.app.state.queue.enqueue(
                endpoint="/v1/videos",
                model=model,
                request_id=request.state.request_id,
                key_id=key_id,
                timeout=settings.timeouts.video,
                operation=operation,
            )
            created = True
        if future:
            future.add_done_callback(_consume_future)
        job = request.app.state.database.get_job(job_id)
        status_code = 202 if job["status"] in {"queued", "running"} else 200
        return JSONResponse(
            status_code=status_code,
            content=video_task_payload(job, replay=not created),
        )
    except QueueFullError:
        return openai_error(429, "platform FIFO queue is full", "queue_full")
    except QueuePausedError:
        return openai_error(503, "platform FIFO queue is paused", "queue_paused")


@app.get(
    "/v1/videos/{task_id}",
    tags=["OpenAI compatible"],
    response_model=VideoTaskResponse,
)
async def get_video(task_id: str, request: Request, key_id: str = Depends(require_api_key)):
    job = request.app.state.database.get_job(task_id)
    if (
        not job
        or job["key_id"] != key_id
        or job["platform"] != settings.platform
        or job["endpoint"] != "/v1/videos"
    ):
        raise HTTPException(status_code=404, detail="video task not found")
    return video_task_payload(job)


@app.get("/v1/videos/{task_id}/content", tags=["OpenAI compatible"])
async def get_video_content(
    task_id: str, request: Request, key_id: str = Depends(require_api_key)
):
    job = request.app.state.database.get_job(task_id)
    if (
        not job
        or job["key_id"] != key_id
        or job["platform"] != settings.platform
        or job["endpoint"] != "/v1/videos"
        or job["status"] != "succeeded"
        or not job["result_location"]
    ):
        raise HTTPException(status_code=404, detail="completed video content not found")
    path = settings.media_dir / Path(job["result_location"]).name
    if not path.is_file():
        raise HTTPException(status_code=410, detail="video content has expired")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/v1/files/{filename}", include_in_schema=False)
async def get_generated_file(filename: str, token: str, request: Request):
    safe_name = Path(filename).name
    if safe_name != filename or not request.app.state.backend.verify_file(safe_name, token):
        raise HTTPException(status_code=403, detail="invalid media token")
    path = settings.media_dir / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="media not found")
    return FileResponse(path)
