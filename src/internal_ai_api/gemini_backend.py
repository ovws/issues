from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .logging_utils import redact


@dataclass(slots=True)
class MediaResult:
    payload: dict[str, Any]
    result_location: str | None = None


class GeminiBackendError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        code: str = "upstream_error",
        pause_queue: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.pause_queue = pause_queue


class GeminiAuthCircuitOpen(GeminiBackendError):
    def __init__(self, message: str = "Gemini authentication circuit is open"):
        super().__init__(
            message,
            status_code=503,
            code="gemini_auth_circuit_open",
            pause_queue=True,
        )


class GeminiRateLimitPaused(GeminiBackendError):
    def __init__(self):
        super().__init__(
            "Gemini rate limit reached; the queue is paused until the service is restarted",
            status_code=429,
            code="gemini_rate_limited",
            pause_queue=True,
        )


class GeminiBackend:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.error: str | None = None
        self.circuit_open = False
        self.refresh_task: asyncio.Task | None = None
        self.last_refresh_at: str | None = None
        self.last_success_at: str | None = None
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
        client = None
        try:
            from gemini_webapi import GeminiClient

            cookie_file = self.settings.gemini_cookie_file
            if not cookie_file or not cookie_file.exists():
                raise RuntimeError(f"Gemini cookie file not found: {cookie_file}")
            values = self._load_cookie_values(cookie_file)
            secure_1psid = values.get("__Secure-1PSID")
            secure_1psidts = values.get("__Secure-1PSIDTS")
            if not secure_1psid or secure_1psid == "replace-locally":
                raise RuntimeError("Gemini __Secure-1PSID is not configured")
            os.environ["GEMINI_COOKIE_PATH"] = str(
                self.settings.media_dir / ".cookie-cache"
            )
            client = GeminiClient(
                secure_1psid,
                secure_1psidts,
                proxy=self.settings.gemini_proxy_url,
            )
            await client.init(
                timeout=self.settings.timeouts.text,
                auto_close=False,
                auto_refresh=False,
            )
            status = getattr(client, "account_status", None)
            if status is not None and getattr(status, "name", "AVAILABLE") != "AVAILABLE":
                raise GeminiAuthCircuitOpen(
                    f"Gemini account is not available ({getattr(status, 'name', 'unknown')})"
                )
            self.client = client
            self.error = None
            self.circuit_open = False
            await self.persist_cookies()
            self.last_success_at = datetime.now(UTC).isoformat()
            self.refresh_task = asyncio.create_task(
                self._refresh_loop(), name="gemini-cookie-refresh"
            )
        except Exception as exc:
            if client:
                await client.close()
            if client is None and isinstance(exc, RuntimeError) and not isinstance(
                exc, GeminiBackendError
            ):
                self.error = redact(exc)
                self.circuit_open = False
            else:
                translated = self._translate_exception(exc)
                self.error = redact(translated)
                self.circuit_open = isinstance(translated, GeminiAuthCircuitOpen)
            self.client = None

    async def close(self) -> None:
        refresh_task = self.refresh_task
        self.refresh_task = None
        if refresh_task and refresh_task is not asyncio.current_task():
            refresh_task.cancel()
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.persist_cookies()
            await self.client.close()
            self.client = None

    @staticmethod
    def _load_cookie_values(cookie_file: Path) -> dict[str, str]:
        payload = json.loads(cookie_file.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("cookies"), dict):
            payload = payload["cookies"]
        if not isinstance(payload, dict):
            raise RuntimeError("Gemini cookie file must contain a JSON object")
        return {
            str(key): str(value)
            for key, value in payload.items()
            if isinstance(value, (str, int, float))
        }

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
                json.dumps(keep, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(temporary, self.settings.gemini_cookie_file)

    async def refresh_once(self) -> None:
        client = self.require_client()
        try:
            from gemini_webapi.exceptions import AuthError
            from gemini_webapi.utils import rotate_1psidts

            refreshed = await rotate_1psidts(client.client, False)
            if not refreshed:
                raise AuthError("Gemini cookie rotation returned no refreshed cookie")
            await self.persist_cookies()
            self.last_refresh_at = datetime.now(UTC).isoformat()
        except Exception as exc:
            translated = self._translate_exception(exc)
            if isinstance(translated, GeminiAuthCircuitOpen):
                await self._trip_auth_circuit(translated)
            raise translated from exc

    async def _refresh_loop(self) -> None:
        interval = max(60, self.settings.gemini_refresh_interval)
        while self.client:
            try:
                await asyncio.sleep(interval)
                await self.refresh_once()
            except asyncio.CancelledError:
                raise
            except GeminiBackendError:
                return

    async def _trip_auth_circuit(self, error: GeminiAuthCircuitOpen) -> None:
        self.circuit_open = True
        self.error = redact(error)
        client = self.client
        self.client = None
        if client:
            await client.close()

    @staticmethod
    def _translate_exception(exc: Exception) -> GeminiBackendError:
        if isinstance(exc, GeminiBackendError):
            return exc
        try:
            from gemini_webapi.exceptions import (
                AuthError,
                TemporarilyBlocked,
                UsageLimitExceeded,
            )

            if isinstance(exc, AuthError):
                return GeminiAuthCircuitOpen()
            if isinstance(exc, (TemporarilyBlocked, UsageLimitExceeded)):
                return GeminiRateLimitPaused()
        except ImportError:
            pass
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        message = redact(exc).lower()
        if status_code in {401, 403} or any(
            marker in message
            for marker in (
                "status code 401",
                "status code 403",
                "unauthenticated",
                "cookie expired",
            )
        ):
            return GeminiAuthCircuitOpen()
        if status_code == 429 or "status code 429" in message:
            return GeminiRateLimitPaused()
        return GeminiBackendError("Gemini upstream operation failed")

    async def _raise_translated(self, exc: Exception) -> None:
        translated = self._translate_exception(exc)
        if isinstance(translated, GeminiAuthCircuitOpen):
            await self._trip_auth_circuit(translated)
        raise translated from exc

    def require_client(self):
        if not self.client:
            if self.circuit_open:
                raise GeminiAuthCircuitOpen()
            raise GeminiBackendError(
                self.error or "Gemini backend is not initialized",
                status_code=503,
                code="gemini_backend_unavailable",
            )
        return self.client

    def account_snapshot(self) -> dict[str, Any]:
        client = self.client
        status = getattr(client, "account_status", None) if client else None
        models = list(client.list_models() or []) if client else []
        return {
            "status": getattr(status, "name", "UNAVAILABLE"),
            "status_code": getattr(status, "value", None),
            "status_description": getattr(status, "description", None),
            "model_count": len(models),
            "models": [
                {
                    "id": getattr(model, "model_name", "")
                    or getattr(model, "display_name", ""),
                    "display_name": getattr(model, "display_name", ""),
                    "available": bool(getattr(model, "is_available", True)),
                    "advanced_only": bool(getattr(model, "advanced_only", False)),
                    "capacity": getattr(model, "capacity", None),
                }
                for model in models
            ],
            "circuit_open": self.circuit_open,
            "last_refresh_at": self.last_refresh_at,
            "last_success_at": self.last_success_at,
            "cookie_file_updated_at": (
                datetime.fromtimestamp(
                    self.settings.gemini_cookie_file.stat().st_mtime, UTC
                ).isoformat()
                if self.settings.gemini_cookie_file
                and self.settings.gemini_cookie_file.exists()
                else None
            ),
        }

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
            {
                "id": name,
                "object": "model",
                "created": now,
                "owned_by": "gemini-web",
            }
            for name in names
        ]

    async def generate(
        self, prompt: str, model: str, files: list[bytes | Path] | None = None
    ):
        client = self.require_client()
        try:
            output = await client.generate_content(
                prompt,
                files=files,
                model=model or self.settings.gemini_default_model,
                temporary=True,
            )
            await self.persist_cookies()
            self.last_success_at = datetime.now(UTC).isoformat()
            return output
        except Exception as exc:
            await self._raise_translated(exc)

    async def save_images(
        self, output, response_format: str, count: int, base_url: str
    ) -> MediaResult:
        items = []
        location = None
        for index, image in enumerate(list(output.images or [])[: max(1, count)]):
            filename = f"img_{secrets.token_hex(12)}_{index}"
            try:
                saved = Path(
                    await image.save(
                        path=str(self.settings.media_dir), filename=filename, verbose=False
                    )
                )
            except Exception as exc:
                await self._raise_translated(exc)
            location = saved.name
            if response_format == "b64_json":
                items.append(
                    {"b64_json": base64.b64encode(saved.read_bytes()).decode("ascii")}
                )
            else:
                token = self.sign(saved.name)
                items.append(
                    {"url": f"{base_url.rstrip('/')}/v1/files/{saved.name}?token={token}"}
                )
        if not items:
            raise RuntimeError("Gemini returned no generated image")
        return MediaResult({"created": int(time.time()), "data": items}, location)

    async def save_video(self, output) -> MediaResult:
        videos = list(output.videos or [])
        if not videos:
            raise RuntimeError("Gemini returned no generated video")
        filename = f"video_{secrets.token_hex(12)}"
        try:
            saved = await videos[0].save(
                path=str(self.settings.media_dir), filename=filename, verbose=False
            )
        except Exception as exc:
            await self._raise_translated(exc)
        location = saved.get("video") if isinstance(saved, dict) else saved
        if not location:
            raise RuntimeError("Gemini video download did not produce a file")
        name = Path(location).name
        return MediaResult({"filename": name}, name)

    def sign(self, filename: str) -> str:
        return hmac.new(self.signing_key, filename.encode(), hashlib.sha256).hexdigest()

    def verify_file(self, filename: str, token: str) -> bool:
        return hmac.compare_digest(self.sign(filename), token)
