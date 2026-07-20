from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi.responses import JSONResponse, Response

VIDEO_MODEL = "grok-imagine-video-1.5"


@dataclass(frozen=True, slots=True)
class VideoChatRequest:
    model: str
    prompt: str
    image_url: str | None
    duration: int
    aspect_ratio: str
    resolution: str
    stream: bool


def parse_video_chat_request(body: bytes) -> VideoChatRequest | None:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("model") != VIDEO_MODEL:
        return None

    prompt = ""
    image_url = None
    messages = payload.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                prompt = content.strip()
            elif isinstance(content, list):
                text_parts: list[str] = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    part_type = part.get("type")
                    if part_type in {"text", "input_text"}:
                        value = part.get("text")
                        if isinstance(value, str) and value.strip():
                            text_parts.append(value.strip())
                    elif part_type in {"image_url", "input_image", "image"}:
                        value: Any = part.get("image_url", part.get("url"))
                        if isinstance(value, dict):
                            value = value.get("url")
                        if isinstance(value, str) and value.strip():
                            image_url = value.strip()
                prompt = "\n".join(text_parts)
            break

    duration = payload.get("duration", 5)
    if not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 15:
        duration = 5
    aspect_ratio = payload.get("aspect_ratio", "16:9")
    if aspect_ratio not in {"1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"}:
        aspect_ratio = "16:9"
    resolution = payload.get("resolution", "720p")
    if resolution not in {"480p", "720p", "1080p"}:
        resolution = "720p"

    return VideoChatRequest(
        model=VIDEO_MODEL,
        prompt=prompt,
        image_url=image_url,
        duration=duration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        stream=payload.get("stream") is True,
    )


def video_payload(value: VideoChatRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": value.model,
        "prompt": value.prompt,
        "duration": value.duration,
        "aspect_ratio": value.aspect_ratio,
        "resolution": value.resolution,
    }
    if value.image_url:
        payload["image"] = {"url": value.image_url}
    return payload


def chat_response(model: str, content: str, *, stream: bool, response_id: str) -> Response:
    created = int(time.time())
    if not stream:
        return JSONResponse(
            {
                "id": response_id,
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )

    first = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}}],
    }
    final = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    body = f"data: {json.dumps(first, ensure_ascii=False)}\n\n"
    body += f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
    body += "data: [DONE]\n\n"
    return Response(content=body, media_type="text/event-stream")
