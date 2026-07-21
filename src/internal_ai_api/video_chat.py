from __future__ import annotations

import base64
import hashlib
import hmac
import math
import re
import struct
from typing import Any

GROK_VIDEO_CHAT_MODEL = "grok-imagine-video-1.5-vision"
GROK_VIDEO_UPSTREAM_MODEL = "grok-imagine-video-1.5"

_VIDEO_RATIOS = {
    "1:1": 1.0,
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "4:3": 4 / 3,
    "3:4": 3 / 4,
    "3:2": 3 / 2,
    "2:3": 2 / 3,
}


def is_grok_video_chat_model(model: object) -> bool:
    return isinstance(model, str) and model.lower() == GROK_VIDEO_CHAT_MODEL


def build_video_request(chat_payload: dict[str, Any]) -> dict[str, Any]:
    messages = chat_payload.get("messages")
    if not isinstance(messages, list):
        messages = chat_payload.get("input")
    if not isinstance(messages, list):
        raise ValueError("视频聊天兼容请求缺少有效 messages 或 input")

    prompt = _last_user_prompt(messages)
    image_url = _last_image_url(messages)
    if not prompt and not image_url:
        raise ValueError("请提供视频描述，或附上一张要制作成视频的图片")

    request: dict[str, Any] = {
        "model": GROK_VIDEO_UPSTREAM_MODEL,
        "prompt": prompt,
    }
    if image_url:
        request["image"] = {"url": image_url}

    duration = _extract_duration(prompt)
    if duration is not None:
        request["duration"] = duration

    resolution = _extract_resolution(prompt)
    if resolution:
        request["resolution"] = resolution

    aspect_ratio = _extract_aspect_ratio(prompt)
    if not aspect_ratio and image_url:
        aspect_ratio = infer_data_image_aspect_ratio(image_url)
    if aspect_ratio:
        request["aspect_ratio"] = aspect_ratio

    return request


def video_access_token(task_id: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), task_id.encode("utf-8"), hashlib.sha256).hexdigest()


def valid_video_access_token(task_id: str, token: str, secret: str) -> bool:
    if not task_id or not token or not secret:
        return False
    return hmac.compare_digest(video_access_token(task_id, secret), token)


def infer_data_image_aspect_ratio(value: str) -> str | None:
    dimensions = _data_image_dimensions(value)
    if not dimensions:
        return None
    width, height = dimensions
    if width <= 0 or height <= 0:
        return None
    ratio = width / height
    return min(_VIDEO_RATIOS, key=lambda name: abs(math.log(ratio / _VIDEO_RATIOS[name])))


def _last_user_prompt(messages: list[Any]) -> str:
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        texts = _content_texts(message.get("content"))
        if texts:
            return "\n".join(texts).strip()
    return ""


def _content_texts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content] if content.strip() and content.strip() != "[Image]" else []
    if not isinstance(content, list):
        return []
    texts: list[str] = []
    for part in content:
        if not isinstance(part, dict) or part.get("type") not in {"text", "input_text"}:
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip() and text.strip() != "[Image]":
            texts.append(text)
    return texts


def _last_image_url(messages: list[Any]) -> str | None:
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in reversed(content):
            image_url = _image_part_url(part)
            if image_url:
                return image_url
    return None


def _image_part_url(part: Any) -> str | None:
    if not isinstance(part, dict) or part.get("type") not in {
        "image_url",
        "input_image",
        "image",
    }:
        return None

    value: Any = None
    for key in ("image_url", "url", "image"):
        candidate = part.get(key)
        if candidate is not None:
            value = candidate
            break
    if isinstance(value, dict):
        value = value.get("url") or value.get("image_url")
    if not isinstance(value, str) or not value.strip():
        return None

    value = value.strip()
    if value.startswith(("data:image/", "http://", "https://")):
        return value
    media_type = part.get("mediaType") or part.get("mime_type") or "image/png"
    return f"data:{media_type};base64,{value}"


def _extract_duration(prompt: str) -> int | None:
    match = re.search(r"(?<![\d.])(1[0-5]|[1-9])\s*(?:秒|s(?:ec(?:ond)?s?)?)(?!\w)", prompt, re.I)
    return int(match.group(1)) if match else None


def _extract_resolution(prompt: str) -> str | None:
    match = re.search(r"(?<!\d)(480|720|1080)\s*p\b", prompt, re.I)
    return f"{match.group(1)}p" if match else None


def _extract_aspect_ratio(prompt: str) -> str | None:
    match = re.search(r"(?<!\d)(16|9|4|3|2|1)\s*:\s*(16|9|4|3|2|1)(?!\d)", prompt)
    if not match:
        return None
    value = f"{match.group(1)}:{match.group(2)}"
    return value if value in _VIDEO_RATIOS else None


def _data_image_dimensions(value: str) -> tuple[int, int] | None:
    if not value.startswith("data:image/") or "," not in value:
        return None
    header, encoded = value.split(",", 1)
    if ";base64" not in header.lower():
        return None
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        return None

    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        return _jpeg_dimensions(data)
    return None


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            return None
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    return None
