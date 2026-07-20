from __future__ import annotations

import json

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

    async def request_json(self, method, path, payload=None):
        request = httpx.Request(method, f"http://upstream{path}")
        if method == "POST":
            assert payload["image"]["url"].startswith("data:image/png;base64,")
            return httpx.Response(
                200,
                request=request,
                json={"request_id": "video_test_1234567890"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"status": "done", "progress": 100},
        )


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

            video_ready = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-imagine-video-1.5",
                    "messages": [{"role": "user", "content": "生成视频"}],
                },
            )
            assert video_ready.status_code == 200
            ready_content = video_ready.json()["choices"][0]["message"]["content"]
            assert "请在当前对话中上传一张图片" in ready_content

            monkeypatch.setattr(app_factory.asyncio, "sleep", _no_sleep)
            video = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "model": "grok-imagine-video-1.5",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "让主体向前移动"},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "data:image/png;base64,AA=="},
                                },
                            ],
                        }
                    ],
                },
            )
            assert video.status_code == 200
            content = video.json()["choices"][0]["message"]["content"]
            assert "/v1/public/videos/video_test_1234567890/content" in content

    paths = app.openapi()["paths"]
    assert "/v1/chat/completions" in paths
    assert "/v1/images/edits" in paths
    video_operation = paths["/v1/videos"]["post"]
    video_schema = video_operation["requestBody"]["content"]["application/json"]["schema"]
    assert video_schema["required"] == ["model", "image"]
    assert video_schema["properties"]["duration"]["maximum"] == 15


async def _no_sleep(_seconds):
    return None
