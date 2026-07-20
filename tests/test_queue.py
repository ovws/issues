from __future__ import annotations

import asyncio

import pytest

from internal_ai_api.config import Timeouts
from internal_ai_api.db import Database
from internal_ai_api.queue import FifoQueue, QueueFullError, QueuePausedError


class Logger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass


def kwargs(operation, request_id="req", timeout=5):
    return {
        "endpoint": "/v1/images/generations",
        "model": "model",
        "request_id": request_id,
        "key_id": "key",
        "timeout": timeout,
        "operation": operation,
    }


def test_video_creation_uses_generation_timeout():
    timeouts = Timeouts(text=1, image=2, edit=3, video=4, status=5)
    assert timeouts.for_path("/v1/videos") == 4
    assert timeouts.for_path("/v1/videos/generations") == 4
    assert timeouts.for_path("/v1/videos/task") == 5


@pytest.mark.asyncio
async def test_pause_exception_stops_dispatch_until_resumed(tmp_path):
    queue = FifoQueue(Database(tmp_path / "paused.db"), "gemini", 2, Logger())
    await queue.start()

    class RateLimited(Exception):
        pause_queue = True

    async def rate_limited():
        raise RateLimited("rate limited")

    with pytest.raises(RateLimited):
        await queue.submit(**kwargs(rate_limited))
    assert queue.health()["paused"] is True

    async def succeeds():
        return "ok"

    with pytest.raises(QueuePausedError):
        await queue.submit(**kwargs(succeeds))
    queue.resume()
    assert await queue.submit(**kwargs(succeeds)) == "ok"
    await queue.stop()


@pytest.mark.asyncio
async def test_fifo_order_and_queue_capacity(tmp_path):
    queue = FifoQueue(Database(tmp_path / "queue.db"), "gemini", 1, Logger())
    await queue.start()
    gate = asyncio.Event()
    order = []

    async def first():
        order.append("first-start")
        await gate.wait()
        order.append("first-end")
        return 1

    async def second():
        order.append("second")
        return 2

    first_task = asyncio.create_task(queue.submit(**kwargs(first, "first")))
    while queue.running_job_id is None:
        await asyncio.sleep(0)
    second_task = asyncio.create_task(queue.submit(**kwargs(second, "second")))
    await asyncio.sleep(0)
    with pytest.raises(QueueFullError):
        queue.enqueue(**kwargs(second, "third"))
    gate.set()
    assert await first_task == 1
    assert await second_task == 2
    assert order == ["first-start", "first-end", "second"]
    await queue.stop()


@pytest.mark.asyncio
async def test_timeout_releases_next_job(tmp_path):
    database = Database(tmp_path / "queue.db")
    queue = FifoQueue(database, "gemini", 2, Logger())
    await queue.start()

    async def never_finishes():
        await asyncio.sleep(60)

    async def succeeds():
        return "ok"

    first = asyncio.create_task(queue.submit(**kwargs(never_finishes, "timeout", timeout=0)))
    second = asyncio.create_task(queue.submit(**kwargs(succeeds, "next")))
    with pytest.raises(TimeoutError):
        await first
    assert await second == "ok"
    assert database.counts()["timed_out"] == 1
    await queue.stop()


@pytest.mark.asyncio
async def test_late_result_cannot_block_or_overwrite_next_job(tmp_path):
    database = Database(tmp_path / "queue.db")
    queue = FifoQueue(database, "gemini", 2, Logger())
    await queue.start()

    async def ignores_cancellation():
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            await asyncio.sleep(0.02)
            return "late"

    async def next_job():
        return "next"

    first = asyncio.create_task(
        queue.submit(**kwargs(ignores_cancellation, "late", timeout=0))
    )
    second = asyncio.create_task(queue.submit(**kwargs(next_job, "next")))
    with pytest.raises(TimeoutError):
        await first
    assert await second == "next"
    await asyncio.sleep(0.03)
    assert database.counts()["timed_out"] == 1
    assert database.counts()["succeeded"] == 1
    await queue.stop()
