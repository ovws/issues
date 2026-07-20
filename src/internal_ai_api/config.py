from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True, slots=True)
class Timeouts:
    text: int
    image: int
    edit: int
    video: int
    status: int

    def for_path(self, path: str) -> int:
        if "/images/edits" in path:
            return self.edit
        if "/images/" in path:
            return self.image
        if "/videos" in path:
            if path.rstrip("/") in {"/v1/videos", "/v1/videos/generations"}:
                return self.video
            return self.status
        return self.text


@dataclass(frozen=True, slots=True)
class Settings:
    platform: str
    title: str
    host: str
    port: int
    db_path: Path
    log_dir: Path
    media_dir: Path
    queue_capacity: int
    max_request_bytes: int
    retention_days: int
    timeouts: Timeouts
    upstream_url: str | None = None
    upstream_api_key: str | None = None
    gemini_cookie_file: Path | None = None
    gemini_proxy_url: str | None = None
    gemini_default_model: str = "gemini-3-flash"
    gemini_video_model: str = "gemini-3-pro"
    gemini_refresh_interval: int = 600
    upstream_failure_threshold: int = 3


def load_settings(platform: str) -> Settings:
    platform = platform.lower()
    if platform not in {"grok", "gemini", "chatgpt-image"}:
        raise ValueError(f"unknown platform: {platform}")

    prefix = platform.upper().replace("-", "_")
    db_dir = Path(_env("INTERNAL_AI_DB_DIR", str(ROOT / "data"))).resolve()
    log_dir = Path(_env("INTERNAL_AI_LOG_DIR", str(ROOT / "logs"))).resolve()
    media_dir = Path(_env("INTERNAL_AI_MEDIA_DIR", str(ROOT / "data" / "media"))).resolve()
    titles = {
        "grok": "Grok Internal API",
        "gemini": "Gemini Internal API",
        "chatgpt-image": "ChatGPT Image Internal API",
    }
    default_ports = {"grok": 8001, "gemini": 8002, "chatgpt-image": 8003}
    upstream_names = {"grok": "GROK", "chatgpt-image": "CHATGPT_IMAGE"}
    upstream_prefix = upstream_names.get(platform)

    return Settings(
        platform=platform,
        title=titles[platform],
        host=_env("INTERNAL_AI_HOST", "0.0.0.0"),
        port=_int(f"{prefix}_PORT", default_ports[platform]),
        db_path=db_dir / f"{platform}.db",
        log_dir=log_dir / platform,
        media_dir=media_dir / platform,
        queue_capacity=_int("INTERNAL_AI_QUEUE_CAPACITY", 100),
        max_request_bytes=_int("INTERNAL_AI_MAX_REQUEST_BYTES", 33_554_432),
        retention_days=_int("INTERNAL_AI_RETENTION_DAYS", 7),
        timeouts=Timeouts(
            text=_int("INTERNAL_AI_TEXT_TIMEOUT_SECONDS", 300),
            image=_int("INTERNAL_AI_IMAGE_TIMEOUT_SECONDS", 900),
            edit=_int("INTERNAL_AI_EDIT_TIMEOUT_SECONDS", 1200),
            video=_int("INTERNAL_AI_VIDEO_TIMEOUT_SECONDS", 3600),
            status=_int("INTERNAL_AI_STATUS_TIMEOUT_SECONDS", 60),
        ),
        upstream_url=(
            _env(f"{upstream_prefix}_UPSTREAM_URL", "").rstrip("/")
            if upstream_prefix
            else None
        ),
        upstream_api_key=(
            _env(f"{upstream_prefix}_UPSTREAM_API_KEY", "") if upstream_prefix else None
        ),
        gemini_cookie_file=(
            Path(
                _env(
                    "GEMINI_COOKIE_FILE",
                    str(ROOT / "config" / "gemini-cookies.local.json"),
                )
            ).resolve()
            if platform == "gemini"
            else None
        ),
        gemini_proxy_url=_env("GEMINI_PROXY_URL", "") or None,
        gemini_default_model=_env("GEMINI_DEFAULT_MODEL", "gemini-3-flash"),
        gemini_video_model=_env("GEMINI_VIDEO_MODEL", "gemini-3-pro"),
        gemini_refresh_interval=_int("GEMINI_REFRESH_INTERVAL_SECONDS", 600),
        upstream_failure_threshold=max(
            1,
            _int(f"{prefix}_FAILURE_THRESHOLD", 3),
        ),
    )
