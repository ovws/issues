from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from internal_ai_api.config import Settings, Timeouts
from internal_ai_api.gemini_backend import MediaResult


class FakeGeminiBackend:
    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.error = None
        self.prompts: list[tuple[str, list[Path]]] = []
        self.requested_models: list[str] = []
        self.generate_images = False

    async def start(self):
        self.client = object()

    async def close(self):
        self.client = None

    def account_snapshot(self):
        return {
            "status": "AVAILABLE",
            "status_code": 1000,
            "status_description": "test account",
            "model_count": 1,
            "models": [],
            "circuit_open": False,
            "last_refresh_at": None,
            "last_success_at": None,
            "cookie_file_updated_at": None,
        }

    def models(self):
        return [
            {
                "id": "gemini-test",
                "object": "model",
                "created": 1,
                "owned_by": "gemini-web",
            }
        ]

    async def generate(self, prompt, model, files=None):
        self.prompts.append((prompt, list(files or [])))
        self.requested_models.append(model)
        images = [object()] if self.generate_images else []
        return SimpleNamespace(text="fake answer", images=images, videos=[])

    async def save_images(self, output, response_format, count, base_url):
        if response_format == "b64_json":
            data = [{"b64_json": "aGVsbG8="}]
        else:
            data = [{"url": f"{base_url.rstrip('/')}/v1/files/fake.png?token=signed"}]
        return MediaResult({"created": 1, "data": data})

    async def save_video(self, output):
        path = self.settings.media_dir / "video_test.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake mp4")
        return MediaResult({"filename": path.name}, path.name)

    def verify_file(self, filename, token):
        return filename == "fake.png" and token == "signed"


def gemini_settings(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text("{}", encoding="utf-8")
    return Settings(
        platform="gemini",
        title="Gemini Test",
        host="127.0.0.1",
        port=8002,
        db_path=tmp_path / "gemini.db",
        log_dir=tmp_path / "logs",
        media_dir=tmp_path / "media",
        queue_capacity=4,
        max_request_bytes=1024 * 1024,
        retention_days=7,
        timeouts=Timeouts(text=5, image=5, edit=5, video=5, status=5),
        gemini_cookie_file=cookie_file,
        gemini_default_model="gemini-test",
    )


@pytest.mark.asyncio
async def test_gemini_openapi_and_end_to_end_routes(monkeypatch, tmp_path):
    from internal_ai_api import gemini_app

    monkeypatch.setattr(gemini_app, "settings", gemini_settings(tmp_path))
    monkeypatch.setattr(gemini_app, "GeminiBackend", FakeGeminiBackend)
    app = gemini_app.app
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            openapi = (await client.get("/openapi.json")).json()
            assert openapi["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
            chat_schema = openapi["paths"]["/v1/chat/completions"]["post"]["requestBody"]
            assert "ChatCompletionRequest" in str(chat_schema)
            assert (await client.get("/docs")).status_code == 200
            assert (await client.get("/v1/models")).status_code == 401

            key = app.state.database.create_api_key("Agent Tester")
            headers = {"Authorization": f"Bearer {key}"}
            models = await client.get("/v1/models", headers=headers)
            assert models.json()["data"][0]["id"] == "gemini-test"

            chat = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gemini-test",
                    "messages": [
                        {"role": "user", "content": "first turn"},
                        {"role": "assistant", "content": "first answer"},
                        {"role": "user", "content": "second turn"},
                    ],
                },
            )
            assert chat.status_code == 200
            assert chat.json()["choices"][0]["message"]["content"] == "fake answer"
            assert "user: first turn" in app.state.backend.prompts[-1][0]
            assert "user: second turn" in app.state.backend.prompts[-1][0]

            png = b"\x89PNG\r\n\x1a\n" + b"test-image"
            multimodal = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gemini-test",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "describe this"},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": "data:image/png;base64,"
                                        + base64.b64encode(png).decode("ascii")
                                    },
                                },
                            ],
                        }
                    ],
                },
            )
            assert multimodal.status_code == 200
            multimodal_prompt, multimodal_files = app.state.backend.prompts[-1]
            assert "describe this" in multimodal_prompt
            assert "[image attached]" in multimodal_prompt
            assert len(multimodal_files) == 1
            assert multimodal_files[0].suffix == ".png"
            assert not multimodal_files[0].exists()

            app.state.backend.generate_images = True
            generated_in_chat = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gemini-test",
                    "messages": [{"role": "user", "content": "draw a red panda"}],
                },
            )
            app.state.backend.generate_images = False
            assert generated_in_chat.status_code == 200
            generated_content = generated_in_chat.json()["choices"][0]["message"]["content"]
            assert "fake answer" in generated_content
            assert "![generated image 1](http://test/v1/files/fake.png?token=signed)" in (
                generated_content
            )

            generated = await client.post(
                "/v1/images/generations",
                headers=headers,
                json={"prompt": "draw a test", "response_format": "b64_json"},
            )
            assert generated.status_code == 200
            assert generated.json()["data"][0]["b64_json"] == "aGVsbG8="

            edited = await client.post(
                "/v1/images/edits",
                headers=headers,
                data={"prompt": "make it blue", "response_format": "url"},
                files={"image": ("input.png", b"png", "image/png")},
            )
            assert edited.status_code == 200
            assert edited.json()["data"][0]["url"].startswith("http://test/v1/files/")

            video_headers = {**headers, "Idempotency-Key": "same-video-request"}
            first = await client.post(
                "/v1/videos", headers=video_headers, json={"prompt": "make a video"}
            )
            second = await client.post(
                "/v1/videos", headers=video_headers, json={"prompt": "make a video"}
            )
            assert first.json()["id"] == second.json()["id"]
            assert second.json()["idempotent_replay"] is True

            task_id = first.json()["id"]
            for _ in range(20):
                status = await client.get(f"/v1/videos/{task_id}", headers=headers)
                if status.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.01)
            assert status.json()["status"] == "completed"
            assert app.state.backend.requested_models[-1] == "gemini-3-pro"
            content = await client.get(f"/v1/videos/{task_id}/content", headers=headers)
            assert content.status_code == 200
            assert content.content == b"fake mp4"

            health = (await client.get("/health")).json()
            assert health["status"] == "ok"
            assert health["account"]["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_gemini_validation_and_unsupported_features(monkeypatch, tmp_path):
    from internal_ai_api import gemini_app

    monkeypatch.setattr(gemini_app, "settings", gemini_settings(tmp_path))
    monkeypatch.setattr(gemini_app, "GeminiBackend", FakeGeminiBackend)
    app = gemini_app.app
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        key = app.state.database.create_api_key("Validation Tester")
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            missing_messages = await client.post(
                "/v1/chat/completions", headers=headers, json={"model": "gemini-test"}
            )
            assert missing_messages.status_code == 400
            assert missing_messages.json()["error"]["type"] == "invalid_request"

            streaming = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
            )
            assert streaming.status_code == 200
            assert streaming.headers["content-type"].startswith("text/event-stream")
            assert '"object":"chat.completion.chunk"' in streaming.text
            assert '"content":"fake answer"' in streaming.text
            assert "data: [DONE]" in streaming.text

            unsupported_block = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "input_audio", "input_audio": {}}],
                        }
                    ]
                },
            )
            assert unsupported_block.status_code == 400
            assert unsupported_block.json()["error"] == {
                "message": "unsupported content block type 'input_audio'",
                "type": "unsupported_content_type",
                "code": None,
            }

            private_image = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": "http://127.0.0.1/private.png",
                                }
                            ],
                        }
                    ]
                },
            )
            assert private_image.status_code == 400
            assert private_image.json()["error"]["type"] == "unsafe_image_url"

            png = b"\x89PNG\r\n\x1a\n" + b"not-a-jpeg"
            spoofed_image = await client.post(
                "/v1/chat/completions",
                headers=headers,
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": "data:image/jpeg;base64,"
                                    + base64.b64encode(png).decode("ascii"),
                                }
                            ],
                        }
                    ]
                },
            )
            assert spoofed_image.status_code == 400
            assert spoofed_image.json()["error"]["type"] == "invalid_image_data"
