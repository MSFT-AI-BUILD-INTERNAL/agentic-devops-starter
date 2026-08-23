"""Pydantic models for Anthropic Messages API compatibility layer."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnthropicMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]


class AnthropicMessagesRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    system: str | list[dict[str, Any]] | None = None
    max_tokens: int = 4096
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None


class AnthropicUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicCountTokensRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    system: str | list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None


class AnthropicCountTokensResponse(BaseModel):
    input_tokens: int


class AnthropicTextContentBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class AnthropicMessagesResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:24]}")
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    model: str
    content: list[AnthropicTextContentBlock]
    stop_reason: str | None = "end_turn"
    stop_sequence: str | None = None
    usage: AnthropicUsage = Field(default_factory=AnthropicUsage)


class AnthropicModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str = "github-copilot"


class AnthropicModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[AnthropicModelInfo]
