from __future__ import annotations

import json

import pytest

from internal_ai_api.config import Settings, Timeouts
from internal_ai_api.gemini_backend import (
    GeminiAuthCircuitOpen,
    GeminiBackend,
    GeminiRateLimitPaused,
)


def settings(tmp_path, cookie_file):
    return Settings(
        platform="gemini",
        title="Gemini",
        host="127.0.0.1",
        port=8002,
        db_path=tmp_path / "gemini.db",
        log_dir=tmp_path / "logs",
        media_dir=tmp_path / "media",
        queue_capacity=2,
        max_request_bytes=1024,
        retention_days=7,
        timeouts=Timeouts(text=5, image=5, edit=5, video=5, status=5),
        gemini_cookie_file=cookie_file,
    )


@pytest.mark.asyncio
async def test_missing_real_cookie_starts_degraded_without_leaking(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps({"__Secure-1PSID": "replace-locally"}), encoding="utf-8"
    )
    backend = GeminiBackend(settings(tmp_path, cookie_file))
    await backend.start()
    assert backend.client is None
    assert "not configured" in backend.error


def test_cookie_loader_accepts_wrapped_format(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps({"cookies": {"__Secure-1PSID": "secret", "ignored": [1]}}),
        encoding="utf-8",
    )
    assert GeminiBackend._load_cookie_values(cookie_file) == {
        "__Secure-1PSID": "secret"
    }


def test_auth_and_rate_limit_errors_request_queue_pause():
    from gemini_webapi.exceptions import AuthError, TemporarilyBlocked, UsageLimitExceeded

    auth = GeminiBackend._translate_exception(AuthError("private cookie text"))
    blocked = GeminiBackend._translate_exception(TemporarilyBlocked("blocked"))
    limited = GeminiBackend._translate_exception(UsageLimitExceeded("limited"))
    assert isinstance(auth, GeminiAuthCircuitOpen)
    assert isinstance(blocked, GeminiRateLimitPaused)
    assert isinstance(limited, GeminiRateLimitPaused)
    assert auth.pause_queue is True
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_refresh_persists_rotated_cookie(monkeypatch, tmp_path):
    from gemini_webapi import utils

    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps({"__Secure-1PSID": "old", "__Secure-1PSIDTS": "old-ts"}),
        encoding="utf-8",
    )
    backend = GeminiBackend(settings(tmp_path, cookie_file))

    class Cookies:
        def get_dict(self):
            return {"__Secure-1PSID": "old", "__Secure-1PSIDTS": "new-ts"}

    class Client:
        def __init__(self):
            self.client = object()
            self.cookies = Cookies()

    async def rotate(client, verbose):
        return "new-ts"

    monkeypatch.setattr(utils, "rotate_1psidts", rotate)
    backend.client = Client()
    await backend.refresh_once()
    saved = json.loads(cookie_file.read_text(encoding="utf-8"))
    assert saved["__Secure-1PSIDTS"] == "new-ts"
    assert backend.last_refresh_at is not None
