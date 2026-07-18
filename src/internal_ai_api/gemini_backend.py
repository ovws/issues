from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings


@dataclass(slots=True)
class MediaResult:
    payload: dict[str, Any]
    result_location: str | None = None


class GeminiBackend:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.error: str | None = None
        self.signing_key_path = settings.media_dir / ".signing-key"
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        self.signing_key = self._load_signing_key()

    def _load_signing_key(self) -> bytes:
        if self.signing_key_path.exists():
            return self.signing_key_path.read_bytes()
        key = secrets.token_bytes(32)
        self.signing_key_path.write_bytes(key)
        return key

    async def start(self) -> None:
        try:
            from gemini_webapi import GeminiClient

            cookie_file = self.settings.gemini_cookie_file
            if not cookie_file or not cookie_file.exists():
                raise RuntimeError(f"Gemini cookie file not found: {cookie_file}")
            values = json.loads(cookie_file.read_text(encoding="utf-8"))
            secure_1psid = values.get("__Secure-1PSID")
            secure_1psidts = values.get("__Secure-1PSIDTS")
            if not secure_1psid or secure_1psid == "replace-locally":
                raise RuntimeError("Gemini __Secure-1PSID is not configured")
            self.client = GeminiClient(
                secure_1psid,
                secure_1psidts,
                proxy=self.settings.gemini_proxy_url,
            )
            await self.client.init(
                timeout=self.settings.timeouts.text,
                auto_close=False,
                auto_refresh=True,
                refresh_interval=600,
            )
            self.error = None
        except Exception as exc:
            self.error = str(exc)
            self.client = None

    async def close(self) -> None:
        if self.client:
            await self.persist_cookies()
            await self.client.close()

    async def persist_cookies(self) -> None:
        if not self.client or not self.settings.gemini_cookie_file:
            return
        cookies = self.client.cookies.get_dict()
        keep = {
            key: value
            for key, value in cookies.items()
            if key in {"__Secure-1PSID", "__Secure-1PSIDTS"}
        }
        if keep:
            temporary = self.settings.gemini_cookie_file.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(keep, indent=2), encoding="utf-8"
            )
            os.replace(temporary, self.settings.gemini_cookie_file)

    def require_client(self):
        if not self.client:
            raise RuntimeError(self.error or "Gemini backend is not initialized")
        return self.client

    def models(self) -> list[dict[str, Any]]:
        client = self.require_client()
        available = client.list_models() or []
        names = []
        for model in available:
            name = getattr(model, "model_name", None) or getattr(model, "name", None)
            if name and name not in names:
                names.append(name)
        if self.settings.gemini_default_model not in names:
            names.insert(0, self.settings.gemini_default_model)
        now = int(time.time())
        return [
            {"id": name, "object": "model", "created": now, "owned_by": "gemini-web"}
            for name in names
        ]

    async def generate(
        self, prompt: str, model: str, files: list[bytes | Path] | None = None
    ):
        client = self.require_client()
        output = await client.generate_content(
            prompt,
            files=files,
            model=model or self.settings.gemini_default_model,
            temporary=True,
        )
        await self.persist_cookies()
        return output

    async def save_images(
        self, output, response_format: str, count: int, base_url: str
    ) -> MediaResult:
        items = []
        location = None
        for index, image in enumerate(list(output.images or [])[: max(1, count)]):
            filename = f"img_{secrets.token_hex(12)}_{index}.png"
            saved = Path(
                await image.save(
                    path=str(self.settings.media_dir), filename=filename, verbose=False
                )
            )
            location = saved.name
            if response_format == "b64_json":
                items.append({"b64_json": base64.b64encode(saved.read_bytes()).decode("ascii")})
            else:
                token = self.sign(saved.name)
                items.append({"url": f"{base_url}v1/files/{saved.name}?token={token}"})
        if not items:
            raise RuntimeError("Gemini returned no generated image")
        return MediaResult({"created": int(time.time()), "data": items}, location)

    async def save_video(self, output) -> MediaResult:
        videos = list(output.videos or [])
        if not videos:
            raise RuntimeError("Gemini returned no generated video")
        filename = f"video_{secrets.token_hex(12)}.mp4"
        saved = await videos[0].save(
            path=str(self.settings.media_dir), filename=filename, verbose=False
        )
        location = saved.get("video") if isinstance(saved, dict) else saved
        if not location:
            raise RuntimeError("Gemini video download did not produce a file")
        name = Path(location).name
        return MediaResult({"filename": name}, name)

    def sign(self, filename: str) -> str:
        return hmac.new(self.signing_key, filename.encode(), hashlib.sha256).hexdigest()

    def verify_file(self, filename: str, token: str) -> bool:
        return hmac.compare_digest(self.sign(filename), token)
