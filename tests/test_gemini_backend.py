from __future__ import annotations

import json

import pytest

from internal_ai_api.config import Settings, Timeouts
from internal_ai_api.gemini_backend import GeminiBackend


@pytest.mark.asyncio
async def test_missing_real_cookie_starts_degraded_without_leaking(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps({"__Secure-1PSID": "replace-locally"}), encoding="utf-8"
    )
    settings = Settings(
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
    backend = GeminiBackend(settings)
    await backend.start()
    assert backend.client is None
    assert "not configured" in backend.error

