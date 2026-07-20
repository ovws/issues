from __future__ import annotations

import json
from collections import deque
from dataclasses import replace

import httpx
import pytest
from fastapi.responses import Response

from internal_ai_api import app_factory
from internal_ai_api.config import Settings, Timeouts
from internal_ai_api.proxy import ProxyResult


class FakeProxy:
    responses: deque[int | Exception] = deque()
    calls: list[str] = []

    def __init__(self, base_url, api_key, client, **kwargs):
        pass

    async def forward(self, request, path, body=None):
        self.calls.append(path)
        scripted = self.responses.popleft() if self.responses else 200
        if isinstance(scripted, Exception):
            raise scripted
        payload = {"path": path, "method": request.method}
        return ProxyResult(
            Response(
                json.dumps(payload),
                status_code=scripted,
                media_type="application/json",
            ),
            result_location="result_id",
        )

    @classmethod
    def reset(cls):
        cls.responses.clear()
        cls.calls.clear()


def settings(tmp_path):
    return Settings(
        platform="grok",
        title="Test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "test.db",
        log_dir=tmp_path / "logs",
        media_dir=tmp_path / "media",
        queue_capacity=2,
        max_request_bytes=1024 * 1024,
        retention_days=7,
        timeouts=Timeouts(text=5, image=5, edit=5, video=5, status=5),
        upstream_url="http://127.0.0.1:1",
        upstream_api_key="upstream-secret",
    )


@pytest.mark.asyncio
async def test_health_auth_and_queued_generation(monkeypatch, tmp_path):
    FakeProxy.reset()
    monkeypatch.setattr(app_factory, "UpstreamProxy", FakeProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/health")).status_code == 200
            assert (await client.get("/v1/models")).status_code == 401

            key = app.state.database.create_api_key("Tester")
            headers = {"Authorization": f"Bearer {key}"}
            models = await client.get("/v1/models", headers=headers)
            assert models.status_code == 200
            assert models.json()["path"] == "/v1/models"

            generated = await client.post(
                "/v1/images/generations",
                headers=headers,
                json={"model": "grok-image", "prompt": "test"},
            )
            assert generated.status_code == 200
            assert app.state.database.counts()["succeeded"] == 1

    paths = app.openapi()["paths"]
    assert "/v1/chat/completions" in paths
    assert "/v1/images/edits" in paths


@pytest.mark.asyncio
async def test_media_writes_require_auth_and_generation_is_idempotent(monkeypatch, tmp_path):
    FakeProxy.reset()
    monkeypatch.setattr(app_factory, "UpstreamProxy", FakeProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/v1/media/result.png")).status_code == 200
            assert (await client.put("/v1/media/upload.bin", content=b"data")).status_code == 401

            key = app.state.database.create_api_key("Tester")
            headers = {"Authorization": f"Bearer {key}"}
            assert (
                await client.put("/v1/media/upload.bin", headers=headers, content=b"data")
            ).status_code == 200

            idempotent_headers = {**headers, "Idempotency-Key": "same-image"}
            first = await client.post(
                "/v1/images/generations",
                headers=idempotent_headers,
                json={"model": "grok-image", "prompt": "test"},
            )
            duplicate = await client.post(
                "/v1/images/generations",
                headers=idempotent_headers,
                json={"model": "grok-image", "prompt": "test"},
            )
            assert first.status_code == 200
            assert first.headers["x-internal-job-id"].startswith("job_")
            assert duplicate.status_code == 409
            assert duplicate.json()["error"]["type"] == "duplicate_request"
            assert duplicate.headers["x-internal-job-id"] == first.headers[
                "x-internal-job-id"
            ]


@pytest.mark.asyncio
async def test_video_requires_idempotency_and_replays_upstream_task_id(monkeypatch, tmp_path):
    FakeProxy.reset()
    monkeypatch.setattr(app_factory, "UpstreamProxy", FakeProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Video tester")
            headers = {"Authorization": f"Bearer {key}"}
            missing = await client.post("/v1/videos", headers=headers, json={"prompt": "x"})
            assert missing.status_code == 400
            assert missing.json()["error"]["type"] == "idempotency_key_required"

            video_headers = {**headers, "Idempotency-Key": "video-once"}
            first = await client.post(
                "/v1/videos", headers=video_headers, json={"prompt": "x"}
            )
            replay = await client.post(
                "/v1/videos", headers=video_headers, json={"prompt": "x"}
            )
            assert first.status_code == 200
            assert replay.status_code == 200
            assert replay.json()["id"] == "result_id"
            assert replay.json()["idempotent_replay"] is True
            assert FakeProxy.calls.count("/v1/videos/generations") == 1


@pytest.mark.asyncio
async def test_safe_reads_retry_once_but_client_auth_failure_does_not_pause_grok(
    monkeypatch, tmp_path
):
    FakeProxy.reset()
    monkeypatch.setattr(app_factory, "UpstreamProxy", FakeProxy)
    configured = replace(
        settings(tmp_path),
        upstream_safe_retries=1,
        upstream_retry_backoff_seconds=0,
    )
    app = app_factory.create_proxy_app(configured)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Tester")
            headers = {"Authorization": f"Bearer {key}"}
            FakeProxy.responses.extend([503, 200])
            assert (await client.get("/v1/models", headers=headers)).status_code == 200
            assert FakeProxy.calls.count("/v1/models") == 2

            FakeProxy.responses.append(401)
            blocked = await client.post(
                "/v1/images/generations", headers=headers, json={"prompt": "x"}
            )
            assert blocked.status_code == 401
            health = (await client.get("/health")).json()
            assert health["status"] == "ok"
            assert health["operator_action_required"] is False
