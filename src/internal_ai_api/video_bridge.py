from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Literal

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
    api_style: Literal["chat", "responses"] = "chat"


def _content_values(content: Any) -> tuple[str, str | None]:
    if isinstance(content, str):
        return content.strip(), None
    if not isinstance(content, list):
        return "", None

    text_parts: list[str] = []
    image_url = None
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
    return "\n".join(text_parts), image_url


def _video_request(
    payload: dict[str, Any],
    prompt: str,
    image_url: str | None,
    api_style: Literal["chat", "responses"],
) -> VideoChatRequest:
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
        api_style=api_style,
    )


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
            prompt, image_url = _content_values(message.get("content"))
            break

    return _video_request(payload, prompt, image_url, "chat")


def parse_video_responses_request(body: bytes) -> VideoChatRequest | None:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("model") != VIDEO_MODEL:
        return None

    request_input = payload.get("input")
    prompt = ""
    image_url = None
    if isinstance(request_input, str):
        prompt = request_input.strip()
    elif isinstance(request_input, list):
        for item in reversed(request_input):
            if not isinstance(item, dict) or item.get("role") not in {None, "user"}:
                continue
            item_prompt, item_image = _content_values(item.get("content", [item]))
            if item_prompt or item_image:
                prompt = item_prompt
                image_url = item_image
                break

    return _video_request(payload, prompt, image_url, "responses")


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


def responses_response(model: str, content: str, *, stream: bool, response_id: str) -> Response:
    created = int(time.time())
    message_id = response_id.replace("resp_", "msg_", 1)
    output_text = {"type": "output_text", "text": content, "annotations": []}
    output_item = {
        "id": message_id,
        "type": "message",
        "status": "completed",
        "role": "assistant",
        "content": [output_text],
    }
    completed = {
        "id": response_id,
        "object": "response",
        "created_at": created,
        "completed_at": created,
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "max_output_tokens": None,
        "model": model,
        "output": [output_item],
        "parallel_tool_calls": True,
        "previous_response_id": None,
        "store": False,
        "temperature": 1.0,
        "text": {"format": {"type": "text"}},
        "tool_choice": "auto",
        "tools": [],
        "top_p": 1.0,
        "truncation": "disabled",
        "usage": {
            "input_tokens": 0,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens": 0,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 0,
        },
        "metadata": {},
    }
    if not stream:
        return JSONResponse(completed)

    in_progress = dict(completed)
    in_progress.update({"completed_at": None, "status": "in_progress", "output": []})
    pending_item = dict(output_item)
    pending_item.update({"status": "in_progress", "content": []})
    empty_part = {"type": "output_text", "text": "", "annotations": []}
    events = [
        {"type": "response.created", "response": in_progress},
        {"type": "response.output_item.added", "output_index": 0, "item": pending_item},
        {
            "type": "response.content_part.added",
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "part": empty_part,
        },
        {
            "type": "response.output_text.delta",
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "delta": content,
        },
        {
            "type": "response.output_text.done",
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "text": content,
        },
        {
            "type": "response.content_part.done",
            "item_id": message_id,
            "output_index": 0,
            "content_index": 0,
            "part": output_text,
        },
        {"type": "response.output_item.done", "output_index": 0, "item": output_item},
        {"type": "response.completed", "response": completed},
    ]
    body_parts: list[str] = []
    for sequence_number, event in enumerate(events):
        event["sequence_number"] = sequence_number
        body_parts.append(
            f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        )
    return Response(content="".join(body_parts), media_type="text/event-stream")


def video_response(value: VideoChatRequest, content: str, *, response_id: str) -> Response:
    if value.api_style == "responses":
        return responses_response(
            value.model,
            content,
            stream=value.stream,
            response_id=response_id,
        )
    return chat_response(
        value.model,
        content,
        stream=value.stream,
        response_id=response_id,
    )
