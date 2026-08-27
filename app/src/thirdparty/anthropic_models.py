"""Pydantic models for the Anthropic Messages API compatibility layer.

These model the wire format of Anthropic's ``POST /v1/messages`` API so it
can be translated to/from the OpenAI-shaped payloads the GitHub Copilot API
speaks (see :mod:`src.thirdparty.anthropic_adapter`).
"""

from typing import Any, Literal

from pydantic import BaseModel


class AnthropicMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str | list[dict[str, Any]]


class AnthropicMessagesRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    system: str | list[dict[str, Any]] | None = None
    max_tokens: int = 4096
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: dict[str, Any] | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stop_sequences: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AnthropicCountTokensRequest(BaseModel):
    model: str
    messages: list[AnthropicMessage]
    system: str | list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None


class AnthropicCountTokensResponse(BaseModel):
    input_tokens: int

class AnthropicModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str = "github-copilot"


class AnthropicModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[AnthropicModelInfo]
