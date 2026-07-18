from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .app_factory import openai_error
from .auth import require_api_key
from .config import load_settings
from .db import Database
from .gemini_backend import GeminiBackend
from .logging_utils import configure_logging
from .maintenance import cleanup_loop
from .queue import FifoQueue, QueueFullError
from .request_ids import request_id

settings = load_settings("gemini")
logger = configure_logging(settings.log_dir, settings.platform)
started_at = time.monotonic()


def messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    parts = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", "") for item in content if item.get("type") == "text"
            )
        parts.append(f"{role}: {content}")
    return "\n\n".join(parts)


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
    return {
        "status": "ok" if backend.client else "degraded",
        "platform": settings.platform,
        "uptime_seconds": round(time.monotonic() - started_at, 3),
        "backend_error": backend.error,
        "queue": request.app.state.queue.health(),
        "jobs": request.app.state.database.counts(),
    }


@app.get("/v1/models", tags=["OpenAI compatible"])
async def list_models(request: Request, key_id: str = Depends(require_api_key)):
    try:
        return {"object": "list", "data": request.app.state.backend.models()}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
    except TimeoutError:
        return openai_error(504, "generation timed out and was not retried", "timeout")
    except Exception as exc:
        logger.exception(
            "gemini_operation_failed request_id=%s error=%s",
            request.state.request_id,
            exc,
        )
        return openai_error(502, "Gemini upstream operation failed", "upstream_error")


@app.post("/v1/chat/completions", tags=["OpenAI compatible"])
async def chat_completions(
    payload: dict[str, Any], request: Request, key_id: str = Depends(require_api_key)
):
    if payload.get("stream"):
        return openai_error(400, "stream=true is not supported by this Gemini layer", "unsupported")
    model = payload.get("model") or settings.gemini_default_model
    prompt = messages_to_prompt(payload.get("messages") or [])

    async def operation():
        output = await request.app.state.backend.generate(prompt, model)
        created = int(time.time())
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": output.text or ""},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    return await queued(request, key_id, "/v1/chat/completions", model, operation)


@app.post("/v1/images/generations", tags=["OpenAI compatible"])
async def image_generations(
    payload: dict[str, Any], request: Request, key_id: str = Depends(require_api_key)
):
    model = payload.get("model") or settings.gemini_default_model
    prompt = payload.get("prompt", "")
    count = max(1, min(int(payload.get("n", 1)), 4))
    response_format = payload.get("response_format", "url")

    async def operation():
        output = await request.app.state.backend.generate(
            f"Generate an image. {prompt}", model
        )
        return await request.app.state.backend.save_images(
            output, response_format, count, str(request.base_url)
        )

    result = await queued(request, key_id, "/v1/images/generations", model, operation)
    return result.payload if hasattr(result, "payload") else result


@app.post("/v1/images/edits", tags=["OpenAI compatible"])
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


@app.post("/v1/videos", tags=["OpenAI compatible"])
async def create_video(
    payload: dict[str, Any], request: Request, key_id: str = Depends(require_api_key)
):
    model = payload.get("model") or settings.gemini_default_model
    prompt = payload.get("prompt", "")

    async def operation():
        output = await request.app.state.backend.generate(
            f"Generate a video. {prompt}", model
        )
        return await request.app.state.backend.save_video(output)

    try:
        job_id, future = request.app.state.queue.enqueue(
            endpoint="/v1/videos",
            model=model,
            request_id=request.state.request_id,
            key_id=key_id,
            timeout=settings.timeouts.video,
            operation=operation,
        )
        future.add_done_callback(_consume_future)
        return JSONResponse(status_code=202, content={"id": job_id, "status": "queued"})
    except QueueFullError:
        return openai_error(429, "platform FIFO queue is full", "queue_full")


@app.get("/v1/videos/{task_id}", tags=["OpenAI compatible"])
async def get_video(task_id: str, request: Request, key_id: str = Depends(require_api_key)):
    job = request.app.state.database.get_job(task_id)
    if (
        not job
        or job["key_id"] != key_id
        or job["platform"] != settings.platform
        or job["endpoint"] != "/v1/videos"
    ):
        raise HTTPException(status_code=404, detail="video task not found")
    return {
        "id": task_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["finished_at"],
        "error": job["error"],
    }


@app.get("/v1/videos/{task_id}/content", tags=["OpenAI compatible"])
async def get_video_content(
    task_id: str, request: Request, key_id: str = Depends(require_api_key)
):
    job = request.app.state.database.get_job(task_id)
    if (
        not job
        or job["key_id"] != key_id
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
