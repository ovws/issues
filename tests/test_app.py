from __future__ import annotations

import json
import re

import httpx
import pytest
from fastapi.responses import Response

from internal_ai_api import app_factory
from internal_ai_api.config import Settings, Timeouts
from internal_ai_api.proxy import ProxyResult


class FakeProxy:
    def __init__(self, base_url, api_key, client):
        pass

    async def forward(self, request, path, body=None):
        payload = {"path": path, "method": request.method}
        return ProxyResult(
            Response(json.dumps(payload), media_type="application/json"),
            result_location="result_id",
        )


class CloudflareTimeoutProxy(FakeProxy):
    async def forward(self, request, path, body=None):
        return ProxyResult(
            Response(
                "<html>524 A timeout occurred</html>",
                status_code=524,
                headers={"retry-after": "120"},
                media_type="text/html",
            )
        )


class CloudflareGenerationTimeoutProxy(CloudflareTimeoutProxy):
    pass


class ModelListProxy(FakeProxy):
    async def forward(self, request, path, body=None):
        return ProxyResult(
            Response(
                json.dumps(
                    {
                        "object": "list",
                        "data": [
                            {"id": "grok-4.5", "object": "model"},
                            {"id": "grok-imagine-video-1.5", "object": "model"},
                            {"id": "grok-imagine-video", "object": "model"},
                        ],
                    }
                ),
                media_type="application/json",
            )
        )


class VideoChatProxy(FakeProxy):
    def __init__(self, base_url, api_key, client):
        self.created_payload = None

    async def forward_as(self, request, method, path, body=None):
        if method == "POST" and path == "/v1/videos/generations":
            self.created_payload = json.loads(body)
            return ProxyResult(
                Response(
                    json.dumps({"request_id": "video_test_123"}),
                    media_type="application/json",
                ),
                result_location="video_test_123",
            )
        if method == "GET" and path == "/v1/videos/video_test_123":
            return ProxyResult(
                Response(
                    json.dumps(
                        {
                            "status": "done",
                            "model": "grok-imagine-video-1.5",
                            "progress": 100,
                            "video": {"url": "http://upstream.invalid/video.mp4"},
                        }
                    ),
                    media_type="application/json",
                )
            )
        if method == "GET" and path == "/v1/videos/video_test_123/content":
            return ProxyResult(Response(b"video-bytes", media_type="video/mp4"))
        raise AssertionError(f"unexpected proxy request: {method} {path}")


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

            video = await client.post(
                "/v1/videos",
                headers=headers,
                json={"model": "grok-imagine-video-1.5", "prompt": "test"},
            )
            assert video.status_code == 200
            assert video.json()["path"] == "/v1/videos/generations"

            wrong_video_endpoint = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={"model": "grok-imagine-video-1.5", "messages": []},
            )
            assert wrong_video_endpoint.status_code == 400
            assert wrong_video_endpoint.json()["error"]["type"] == "unsupported"
            assert "POST /v1/videos" in wrong_video_endpoint.json()["error"]["message"]

    paths = app.openapi()["paths"]
    assert "/v1/chat/completions" in paths
    assert "/v1/images/edits" in paths


@pytest.mark.asyncio
async def test_cloudflare_timeout_is_normalized(monkeypatch, tmp_path):
    monkeypatch.setattr(app_factory, "UpstreamProxy", CloudflareTimeoutProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Tester")
            response = await client.get(
                "/v1/models", headers={"Authorization": f"Bearer {key}"}
            )

    assert response.status_code == 504
    assert response.headers["retry-after"] == "120"
    assert response.json()["error"]["type"] == "timeout"


@pytest.mark.asyncio
async def test_cloudflare_generation_timeout_marks_job_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(app_factory, "UpstreamProxy", CloudflareGenerationTimeoutProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Tester")
            response = await client.post(
                "/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "grok-image", "prompt": "test"},
            )

            assert response.status_code == 504
            assert app.state.database.counts()["failed"] == 1


@pytest.mark.asyncio
async def test_video_models_are_not_advertised_as_chat_models(monkeypatch, tmp_path):
    monkeypatch.setattr(app_factory, "UpstreamProxy", ModelListProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Tester")
            response = await client.get(
                "/v1/models", headers={"Authorization": f"Bearer {key}"}
            )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [
        "grok-4.5",
        "grok-imagine-video-1.5-vision",
    ]


@pytest.mark.asyncio
async def test_cherry_video_chat_alias_creates_video_and_returns_public_result(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(app_factory, "UpstreamProxy", VideoChatProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Tester")
            response = await client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "grok-imagine-video-1.5-vision",
                    "stream": True,
                    "messages": [
                        {"role": "assistant", "content": "[Image]"},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "让她自然地动起来，1秒，480p"},
                                {"type": "image_url", "image_url": {"url": image}},
                            ],
                        },
                    ],
                },
            )

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert "视频已生成" in response.text
            assert "data: [DONE]" in response.text
            assert app.state.proxy.created_payload == {
                "model": "grok-imagine-video-1.5",
                "prompt": "让她自然地动起来，1秒，480p",
                "image": {"url": image},
                "duration": 1,
                "resolution": "480p",
                "aspect_ratio": "1:1",
            }

            match = re.search(r"\[打开或下载视频\]\(([^)]+)\)", response.text)
            assert match
            video_response = await client.get(match.group(1))
            assert video_response.status_code == 200
            assert video_response.content == b"video-bytes"
            assert video_response.headers["content-type"] == "video/mp4"


@pytest.mark.asyncio
async def test_cherry_video_responses_alias_uses_responses_stream(monkeypatch, tmp_path):
    monkeypatch.setattr(app_factory, "UpstreamProxy", VideoChatProxy)
    app = app_factory.create_proxy_app(settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            key = app.state.database.create_api_key("Tester")
            response = await client.post(
                "/v1/responses",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "grok-imagine-video-1.5-vision",
                    "stream": True,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": "Animate this woman, 4s, 480p"},
                                {"type": "input_image", "image_url": image},
                            ],
                        }
                    ],
                },
            )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: response.created" in response.text
    assert "event: response.output_item.added" in response.text
    assert "event: response.output_text.delta" in response.text
    assert "event: response.output_item.done" in response.text
    assert "event: response.completed" in response.text
    assert "data: [DONE]" in response.text
    assert app.state.proxy.created_payload == {
        "model": "grok-imagine-video-1.5",
        "prompt": "Animate this woman, 4s, 480p",
        "image": {"url": image},
        "duration": 4,
        "resolution": "480p",
        "aspect_ratio": "1:1",
    }
