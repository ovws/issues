from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .db import Database
from .logging_utils import redact


class QueueFullError(Exception):
    pass


class QueuePausedError(Exception):
    pass


@dataclass(slots=True)
class WorkItem:
    job_id: str
    endpoint: str
    model: str | None
    request_id: str
    key_id: str
    timeout: int
    operation: Callable[[], Awaitable[Any]]
    future: asyncio.Future[Any]


class FifoQueue:
    """A persistent-metadata, in-process FIFO queue with exactly one worker."""

    def __init__(self, database: Database, platform: str, capacity: int, logger):
        self.database = database
        self.platform = platform
        self.queue: asyncio.Queue[WorkItem] = asyncio.Queue(maxsize=capacity)
        self.logger = logger
        self.worker_task: asyncio.Task | None = None
        self.running_job_id: str | None = None
        self.paused_reason: str | None = None
        self.paused_at: str | None = None
        self._resume_event = asyncio.Event()
        self._resume_event.set()

    async def start(self) -> None:
        if not self.worker_task or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker(), name=f"{self.platform}-fifo")

    async def stop(self) -> None:
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None

    def enqueue(
        self,
        *,
        endpoint: str,
        model: str | None,
        request_id: str,
        key_id: str,
        timeout: int,
        operation: Callable[[], Awaitable[Any]],
    ) -> tuple[str, asyncio.Future[Any]]:
        if not self._resume_event.is_set():
            raise QueuePausedError(self.paused_reason or "platform queue is paused")
        if self.queue.full():
            raise QueueFullError("platform queue is full")
        job_id = self.database.create_job(
            self.platform, endpoint, model, request_id, key_id
        )
        future = asyncio.get_running_loop().create_future()
        self.queue.put_nowait(
            WorkItem(job_id, endpoint, model, request_id, key_id, timeout, operation, future)
        )
        return job_id, future

    async def submit(self, **kwargs) -> Any:
        _, future = self.enqueue(**kwargs)
        return await future

    def enqueue_idempotent(
        self,
        *,
        endpoint: str,
        model: str | None,
        request_id: str,
        key_id: str,
        idempotency_key: str,
        timeout: int,
        operation: Callable[[], Awaitable[Any]],
    ) -> tuple[str, asyncio.Future[Any] | None, bool]:
        existing = self.database.get_job_by_idempotency(
            self.platform, endpoint, key_id, idempotency_key
        )
        if existing:
            return existing["job_id"], None, False
        if not self._resume_event.is_set():
            raise QueuePausedError(self.paused_reason or "platform queue is paused")
        if self.queue.full():
            raise QueueFullError("platform queue is full")
        job_id, created = self.database.create_idempotent_job(
            self.platform,
            endpoint,
            model,
            request_id,
            key_id,
            idempotency_key,
        )
        if not created:
            return job_id, None, False
        future = asyncio.get_running_loop().create_future()
        self.queue.put_nowait(
            WorkItem(job_id, endpoint, model, request_id, key_id, timeout, operation, future)
        )
        return job_id, future, True

    def pause(self, reason: object) -> None:
        self.paused_reason = redact(reason)[:500]
        self.paused_at = datetime.now(UTC).isoformat()
        self._resume_event.clear()
        self.logger.warning("queue_paused reason=%s", self.paused_reason)
        while True:
            try:
                item = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            self.database.fail_queued_job(item.job_id, self.paused_reason)
            if not item.future.cancelled():
                item.future.set_exception(QueuePausedError(self.paused_reason))
            self.queue.task_done()

    def resume(self) -> None:
        self.paused_reason = None
        self.paused_at = None
        self._resume_event.set()
        self.logger.info("queue_resumed")

    async def _worker(self) -> None:
        while True:
            await self._resume_event.wait()
            item = await self.queue.get()
            self.running_job_id = item.job_id
            execution_id = self.database.start_job(item.job_id)
            operation_task: asyncio.Task | None = None
            started = time.monotonic()
            self.logger.info(
                (
                    "job_started job_id=%s execution_id=%s request_id=%s key_id=%s "
                    "endpoint=%s model=%s queued=%s"
                ),
                item.job_id,
                execution_id,
                item.request_id,
                item.key_id,
                item.endpoint,
                item.model or "-",
                self.queue.qsize(),
            )
            try:
                operation_task = asyncio.create_task(
                    item.operation(), name=f"{self.platform}-{execution_id}"
                )
                done, _ = await asyncio.wait({operation_task}, timeout=item.timeout)
                if not done:
                    self.database.timeout_job(item.job_id, execution_id)
                    operation_task.cancel()
                    operation_task.add_done_callback(self._consume_late_operation)
                    if not item.future.cancelled():
                        item.future.set_exception(TimeoutError("generation timed out"))
                    self.logger.warning(
                        (
                            "job_timed_out job_id=%s request_id=%s key_id=%s endpoint=%s "
                            "duration_ms=%s timeout=%ss"
                        ),
                        item.job_id,
                        item.request_id,
                        item.key_id,
                        item.endpoint,
                        round((time.monotonic() - started) * 1000),
                        item.timeout,
                    )
                    continue
                result = operation_task.result()
                result_location = getattr(result, "result_location", None)
                accepted = self.database.finish_job(
                    item.job_id,
                    execution_id,
                    "succeeded",
                    result_location=result_location,
                )
                if accepted and not item.future.cancelled():
                    item.future.set_result(result)
                elif not accepted and not item.future.cancelled():
                    item.future.set_exception(RuntimeError("job state was already finalized"))
                self.logger.info(
                    (
                        "job_succeeded job_id=%s request_id=%s key_id=%s endpoint=%s "
                        "duration_ms=%s"
                    ),
                    item.job_id,
                    item.request_id,
                    item.key_id,
                    item.endpoint,
                    round((time.monotonic() - started) * 1000),
                )
            except asyncio.CancelledError:
                if operation_task and not operation_task.done():
                    operation_task.cancel()
                    operation_task.add_done_callback(self._consume_late_operation)
                self.database.finish_job(
                    item.job_id, execution_id, "interrupted", error="service stopped"
                )
                if not item.future.cancelled():
                    item.future.cancel()
                raise
            except Exception as exc:
                safe_error = redact(exc)
                if getattr(exc, "pause_queue", False):
                    self.pause(safe_error)
                self.database.finish_job(
                    item.job_id, execution_id, "failed", error=safe_error
                )
                if not item.future.cancelled():
                    item.future.set_exception(exc)
                self.logger.exception(
                    (
                        "job_failed job_id=%s request_id=%s key_id=%s endpoint=%s "
                        "duration_ms=%s error=%s"
                    ),
                    item.job_id,
                    item.request_id,
                    item.key_id,
                    item.endpoint,
                    round((time.monotonic() - started) * 1000),
                    safe_error,
                )
            finally:
                self.running_job_id = None
                self.queue.task_done()

    def _consume_late_operation(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except (asyncio.CancelledError, Exception):
            pass

    def health(self) -> dict[str, int | str | bool | None]:
        return {
            "queued": self.queue.qsize(),
            "running": int(self.running_job_id is not None),
            "running_job_id": self.running_job_id,
            "capacity": self.queue.maxsize,
            "paused": not self._resume_event.is_set(),
            "paused_reason": self.paused_reason,
            "paused_at": self.paused_at,
        }
