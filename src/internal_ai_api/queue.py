from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .db import Database
from .logging_utils import redact


class QueueFullError(Exception):
    pass


@dataclass(slots=True)
class WorkItem:
    job_id: str
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
        if self.queue.full():
            raise QueueFullError("platform queue is full")
        job_id = self.database.create_job(
            self.platform, endpoint, model, request_id, key_id
        )
        future = asyncio.get_running_loop().create_future()
        self.queue.put_nowait(WorkItem(job_id, timeout, operation, future))
        return job_id, future

    async def submit(self, **kwargs) -> Any:
        _, future = self.enqueue(**kwargs)
        return await future

    async def _worker(self) -> None:
        while True:
            item = await self.queue.get()
            self.running_job_id = item.job_id
            execution_id = self.database.start_job(item.job_id)
            operation_task: asyncio.Task | None = None
            self.logger.info(
                "job_started job_id=%s execution_id=%s queued=%s",
                item.job_id,
                execution_id,
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
                        "job_timed_out job_id=%s timeout=%ss", item.job_id, item.timeout
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
                self.logger.info("job_succeeded job_id=%s", item.job_id)
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
                self.database.finish_job(
                    item.job_id, execution_id, "failed", error=safe_error
                )
                if not item.future.cancelled():
                    item.future.set_exception(exc)
                self.logger.exception("job_failed job_id=%s error=%s", item.job_id, safe_error)
            finally:
                self.running_job_id = None
                self.queue.task_done()

    def _consume_late_operation(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except (asyncio.CancelledError, Exception):
            pass

    def health(self) -> dict[str, int | str | None]:
        return {
            "queued": self.queue.qsize(),
            "running": int(self.running_job_id is not None),
            "running_job_id": self.running_job_id,
            "capacity": self.queue.maxsize,
        }
