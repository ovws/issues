from __future__ import annotations

import asyncio
import base64
import binascii
import ipaddress
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote_to_bytes, urljoin, urlsplit

import httpx

from .config import Settings
from .gemini_schemas import ChatImageURL, ChatMessage

ALLOWED_IMAGE_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGES = 8
MAX_REDIRECTS = 3
DOWNLOAD_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ChatInputError(ValueError):
    def __init__(self, message: str, code: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(slots=True)
class PreparedChatInput:
    prompt: str
    files: list[Path]

    def cleanup(self) -> None:
        for path in self.files:
            path.unlink(missing_ok=True)


def _image_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _validate_image(data: bytes, declared_type: str) -> str:
    media_type = declared_type.partition(";")[0].strip().lower()
    if media_type not in ALLOWED_IMAGE_TYPES:
        raise ChatInputError(
            f"unsupported image MIME type: {media_type or 'missing'}",
            "unsupported_image_type",
        )
    detected_type = _image_type(data)
    if detected_type != media_type:
        raise ChatInputError(
            "image content does not match its declared MIME type",
            "invalid_image_data",
        )
    return media_type


def _is_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


async def _validate_remote_target(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ChatInputError(
            "remote image URL must use http or https", "invalid_image_url"
        )
    if not parsed.hostname or parsed.username or parsed.password:
        raise ChatInputError("remote image URL is invalid", "invalid_image_url")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise ChatInputError("remote image URL has an invalid port", "invalid_image_url") from exc
    try:
        addresses = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(
                parsed.hostname, port, type=socket.SOCK_STREAM
            ),
            timeout=5.0,
        )
    except (OSError, TimeoutError) as exc:
        raise ChatInputError(
            "remote image host could not be resolved", "image_download_failed"
        ) from exc
    if not addresses or any(not _is_public_ip(item[4][0]) for item in addresses):
        raise ChatInputError(
            "remote image URL resolves to a non-public address", "unsafe_image_url"
        )


def _validate_connected_peer(response: httpx.Response) -> None:
    network_stream = response.extensions.get("network_stream")
    if network_stream is None:
        return
    peer = network_stream.get_extra_info("server_addr")
    if peer and not _is_public_ip(str(peer[0])):
        raise ChatInputError(
            "remote image connection used a non-public address", "unsafe_image_url"
        )


class ChatImageLoader:
    def __init__(self, settings: Settings, request_id: str):
        self.remaining_bytes = settings.max_request_bytes
        self.spool_dir = settings.media_dir / ".requests"
        self.request_id = request_id
        self.files: list[Path] = []

    def _store(self, data: bytes, media_type: str) -> Path:
        if not data:
            raise ChatInputError("image content is empty", "invalid_image_data")
        if len(data) > self.remaining_bytes:
            raise ChatInputError(
                "multimodal images are too large", "image_too_large", status_code=413
            )
        self.remaining_bytes -= len(data)
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        path = self.spool_dir / (
            f"{self.request_id}_chat_{len(self.files)}_{secrets.token_hex(6)}"
            f"{ALLOWED_IMAGE_TYPES[media_type]}"
        )
        path.write_bytes(data)
        self.files.append(path)
        return path

    def _load_data_url(self, url: str) -> Path:
        header, separator, encoded = url.partition(",")
        if not separator or not header.lower().startswith("data:image/"):
            raise ChatInputError("image Data URL is invalid", "invalid_image_url")
        metadata = header[5:].split(";")
        media_type = metadata[0].lower()
        try:
            if any(item.lower() == "base64" for item in metadata[1:]):
                data = base64.b64decode(encoded, validate=True)
            else:
                data = unquote_to_bytes(encoded)
        except (binascii.Error, ValueError) as exc:
            raise ChatInputError(
                "image Data URL encoding is invalid", "invalid_image_data"
            ) from exc
        media_type = _validate_image(data, media_type)
        return self._store(data, media_type)

    async def _load_remote_url(self, url: str) -> Path:
        current_url = url
        try:
            async with httpx.AsyncClient(
                follow_redirects=False, timeout=DOWNLOAD_TIMEOUT, trust_env=False
            ) as client:
                for redirect_count in range(MAX_REDIRECTS + 1):
                    await _validate_remote_target(current_url)
                    async with client.stream("GET", current_url) as response:
                        _validate_connected_peer(response)
                        if response.is_redirect:
                            if redirect_count == MAX_REDIRECTS:
                                raise ChatInputError(
                                    "remote image URL redirected too many times",
                                    "image_download_failed",
                                )
                            location = response.headers.get("location")
                            if not location:
                                raise ChatInputError(
                                    "remote image redirect is missing a location",
                                    "image_download_failed",
                                )
                            current_url = urljoin(current_url, location)
                            continue
                        response.raise_for_status()
                        content_length = response.headers.get("content-length")
                        if content_length:
                            try:
                                if int(content_length) > self.remaining_bytes:
                                    raise ChatInputError(
                                        "multimodal images are too large",
                                        "image_too_large",
                                        status_code=413,
                                    )
                            except ValueError as exc:
                                raise ChatInputError(
                                    "remote image has an invalid Content-Length",
                                    "image_download_failed",
                                ) from exc
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > self.remaining_bytes:
                                raise ChatInputError(
                                    "multimodal images are too large",
                                    "image_too_large",
                                    status_code=413,
                                )
                        media_type = _validate_image(
                            bytes(data), response.headers.get("content-type", "")
                        )
                        return self._store(bytes(data), media_type)
        except ChatInputError:
            raise
        except (httpx.HTTPError, OSError) as exc:
            raise ChatInputError(
                "remote image could not be downloaded", "image_download_failed"
            ) from exc
        raise ChatInputError("remote image could not be downloaded", "image_download_failed")

    async def load(self, image_url: ChatImageURL | str) -> Path:
        url = image_url.url if isinstance(image_url, ChatImageURL) else image_url
        if url.startswith("data:"):
            return self._load_data_url(url)
        return await self._load_remote_url(url)

    def cleanup(self) -> None:
        for path in self.files:
            path.unlink(missing_ok=True)


async def prepare_chat_input(
    messages: list[ChatMessage], settings: Settings, request_id: str
) -> PreparedChatInput:
    loader = ChatImageLoader(settings, request_id)
    prompt_parts: list[str] = []
    image_count = 0
    try:
        for message in messages:
            if isinstance(message.content, str):
                content = message.content
            else:
                content_parts: list[str] = []
                for item in message.content:
                    if item.type == "text":
                        content_parts.append(item.text or "")
                    elif item.type == "image_url":
                        image_count += 1
                        if image_count > MAX_IMAGES:
                            raise ChatInputError(
                                f"at most {MAX_IMAGES} images are supported",
                                "too_many_images",
                            )
                        await loader.load(item.image_url)  # type: ignore[arg-type]
                        content_parts.append("[image attached]")
                content = "\n".join(content_parts)
            prompt_parts.append(f"{message.role}: {content}")
        return PreparedChatInput("\n\n".join(prompt_parts), loader.files)
    except Exception:
        loader.cleanup()
        raise
