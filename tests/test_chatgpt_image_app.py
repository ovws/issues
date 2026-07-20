from __future__ import annotations

import json
import logging
from collections import deque

import httpx
import pytest
from fastapi import Request
from fastapi.responses import Response

from internal_ai_api import app_factory
from internal_ai_api.config import Settings, Timeouts
from internal_ai_api.db import Database
from internal_ai_api.proxy import ProxyResult, UpstreamProxy
from internal_ai_api.queue import FifoQueue, QueuePausedError
from internal_ai_api.upstream_guard import UpstreamFailureGuard, UpstreamResponseError


class ScriptedProxy:
    responses: deque[int] = deque()
    calls: list[dict[str, object]] = []

    def __init__(self, base_url, api_key, client):
        self.api_key = api_key

    async def forward(self, request, path, body=None):
        request_body = body if body is not None else await request.body()
        self.calls.append(
            {
                "path": path,
                "body": request_body,
                "content_type": request.headers.get("content-type", ""),
            }
        )
        status = self.responses.popleft() if self.responses else 200
        payload = {
            "path": path,
            "data": [{"url": "http://chatgpt-image.internal/images/result.png"}],
        }
        return ProxyResult(
            Response(json.dumps(payload), status_code=status, media_type="application/json")
        )


def chatgpt_settings(tmp_path) -> Settings:
    return Settings(
        platform="chatgpt-image",
        title="ChatGPT Image Test",
        host="127.0.0.1",
        port=8003,
        db_path=tmp_path / "chatgpt-image.db",
        log_dir=tmp_path / "logs",
        media_dir=tmp_path / "media",
        queue_capacity=4,
        max_request_bytes=2 * 1024 * 1024,
        retention_days=7,
        timeouts=Timeouts(text=5, image=5, edit=5, video=5, status=5),
        upstream_url="http://chatgpt2api",
        upstream_api_key="upstream-master-secret",
        upstream_failure_threshold=3,
    )


@pytest.fixture
async def client(monkeypatch, tmp_path):
    ScriptedProxy.responses.clear()
    ScriptedProxy.calls.clear()
    monkeypatch.setattr(app_factory, "UpstreamProxy", ScriptedProxy)
    app = app_factory.create_proxy_app(chatgpt_settings(tmp_path))
    async with app.router.lifespan_context(app):
        key = app.state.database.create_api_key("Image tester")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as session:
            yield app, session, {"Authorization": f"Bearer {key}"}


@pytest.mark.asyncio
async def test_generation_and_multi_image_edit_are_forwarded_without_shape_changes(client):
    app, session, headers = client
    generated = await session.post(
        "/v1/images/generations",
        headers=headers,
        json={
            "model": "gpt-image-2",
            "prompt": "draw a blue square",
            "n": 2,
            "size": "1024x1024",
            "response_format": "url",
        },
    )
    assert generated.status_code == 200
    assert generated.json()["data"][0]["url"].startswith("http://chatgpt-image.internal/")

    single_edit = await session.post(
        "/v1/images/edits",
        headers=headers,
        data={"model": "gpt-image-2", "prompt": "make it brighter"},
        files={"image": ("single.png", b"single-image", "image/png")},
    )
    assert single_edit.status_code == 200
    assert b'filename="single.png"' in ScriptedProxy.calls[-1]["body"]

    edited = await session.post(
        "/v1/images/edits",
        headers=headers,
        data={"model": "gpt-image-2", "prompt": "combine both references"},
        files=[
            ("image", ("one.png", b"first-image", "image/png")),
            ("image", ("two.png", b"second-image", "image/png")),
        ],
    )
    assert edited.status_code == 200
    call = ScriptedProxy.calls[-1]
    assert call["path"] == "/v1/images/edits"
    assert str(call["content_type"]).startswith("multipart/form-data; boundary=")
    assert b'filename="one.png"' in call["body"]
    assert b'filename="two.png"' in call["body"]
    assert b"first-image" in call["body"]
    assert b"second-image" in call["body"]
    assert app.state.database.counts()["succeeded"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/models"),
        ("POST", "/v1/chat/completions"),
        ("POST", "/v1/responses"),
    ],
)
async def test_required_compatibility_routes(method, path, client):
    _, session, headers = client
    response = await session.request(
        method,
        path,
        headers=headers,
        json={} if method == "POST" else None,
    )
    assert response.status_code == 200
    assert response.json()["path"] == path


@pytest.mark.asyncio
async def test_auth_or_rate_limit_response_pauses_only_the_chatgpt_queue(client):
    app, session, headers = client
    ScriptedProxy.responses.append(429)
    blocked = await session.post(
        "/v1/images/generations",
        headers=headers,
        json={"model": "gpt-image-2", "prompt": "test"},
    )
    assert blocked.status_code == 429

    health = (await session.get("/health")).json()
    assert health["status"] == "paused"
    assert health["operator_action_required"] is True
    assert health["queue"]["paused"] is True

    stopped = await session.post(
        "/v1/images/generations",
        headers=headers,
        json={"model": "gpt-image-2", "prompt": "must not reach upstream"},
    )
    assert stopped.status_code == 503
    assert stopped.json()["error"]["type"] == "queue_paused"
    assert len(ScriptedProxy.calls) == 1
    assert app.state.database.counts()["failed"] == 1


def test_failure_guard_pauses_after_streak_and_success_resets_it():
    guard = UpstreamFailureGuard(failure_threshold=3)

    def result(status: int) -> ProxyResult:
        return ProxyResult(Response(status_code=status))

    for _ in range(2):
        with pytest.raises(UpstreamResponseError) as exc_info:
            guard.inspect(result(502))
        assert exc_info.value.pause_queue is False

    guard.inspect(result(200))
    assert guard.consecutive_failures == 0

    pauses = []
    for _ in range(3):
        with pytest.raises(UpstreamResponseError) as exc_info:
            guard.inspect(result(503))
        pauses.append(exc_info.value.pause_queue)
    assert pauses == [False, False, True]


@pytest.mark.asyncio
async def test_pause_fails_and_drains_waiting_jobs(tmp_path):
    database = Database(tmp_path / "queue.db")
    queue = FifoQueue(database, "chatgpt-image", 4, logging.getLogger("test"))

    async def operation():
        return "unused"

    futures = []
    for index in range(2):
        _, future = queue.enqueue(
            endpoint="/v1/images/generations",
            model="gpt-image-2",
            request_id=f"request-{index}",
            key_id="key-id",
            timeout=5,
            operation=operation,
        )
        futures.append(future)

    queue.pause("operator review")
    assert queue.health()["queued"] == 0
    assert database.counts()["failed"] == 2
    for future in futures:
        with pytest.raises(QueuePausedError):
            await future


@pytest.mark.asyncio
async def test_proxy_replaces_personal_key_with_upstream_master_key():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = request.content
        return httpx.Response(200, json={"data": [{"b64_json": "aW1hZ2U="}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    proxy = UpstreamProxy("http://chatgpt2api", "master-only", client)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/images/generations",
        "query_string": b"",
        "headers": [
            (b"authorization", b"Bearer sk-internal-personal.secret"),
            (b"content-type", b"application/json"),
        ],
    }

    async def receive():
        return {"type": "http.request", "body": b'{"prompt":"test"}', "more_body": False}

    request = Request(scope, receive)
    try:
        response = await proxy.forward(request, "/v1/images/generations")
    finally:
        await client.aclose()

    assert response.response.status_code == 200
    assert json.loads(response.response.body)["data"][0]["b64_json"] == "aW1hZ2U="
    assert captured["authorization"] == "Bearer master-only"
    assert captured["body"] == b'{"prompt":"test"}'
