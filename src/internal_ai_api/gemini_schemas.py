from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError


class ChatImageURL(BaseModel):
    url: str = Field(min_length=1)
    detail: Literal["auto", "low", "high"] | None = None


class ChatContentPart(BaseModel):
    type: str
    text: str | None = None
    image_url: ChatImageURL | str | None = None

    @model_validator(mode="after")
    def validate_content(self):
        if self.type == "text":
            if self.text is None:
                raise PydanticCustomError(
                    "invalid_content_block", "text content block requires 'text'"
                )
            return self
        if self.type == "image_url":
            if self.image_url is None:
                raise PydanticCustomError(
                    "invalid_content_block",
                    "image_url content block requires 'image_url'",
                )
            return self
        raise PydanticCustomError(
            "unsupported_content_type",
            "unsupported content block type '{content_type}'",
            {"content_type": self.type},
        )


class ChatMessage(BaseModel):
    role: Literal["developer", "system", "user", "assistant", "tool"]
    content: str | list[ChatContentPart]
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    stop: str | list[str] | None = None
    user: str | None = None
    tools: list[dict[str, Any]] | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int]


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    n: int = Field(default=1, ge=1, le=4)
    response_format: Literal["url", "b64_json"] = "url"
    size: str | None = None
    quality: str | None = None
    user: str | None = None


class ImageData(BaseModel):
    url: str | None = None
    b64_json: str | None = None


class ImageResponse(BaseModel):
    created: int
    data: list[ImageData]


class VideoCreateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    seconds: int | str | None = None
    size: str | None = None


class VideoTaskResponse(BaseModel):
    id: str
    object: Literal["video"] = "video"
    status: Literal["queued", "in_progress", "completed", "failed"]
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    idempotent_replay: bool = False


class ModelObject(BaseModel):
    id: str
    object: Literal["model"]
    created: int
    owned_by: str


class ModelList(BaseModel):
    object: Literal["list"]
    data: list[ModelObject]
