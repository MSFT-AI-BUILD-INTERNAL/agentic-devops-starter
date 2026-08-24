"""Translate GitHub Copilot chat-completion stream chunks into Anthropic SSE events.

Anthropic SSE sequence for a streaming text response:

    message_start
    content_block_start  (index 0, type "text")
    content_block_delta*  (text_delta)
    content_block_stop    (index 0)
    message_delta         (stop_reason, usage)
    message_stop

Anthropic SSE sequence for a streaming tool-use response:

    message_start
    content_block_start  (index N, type "tool_use")
    content_block_delta* (input_json_delta, partial_json)
    content_block_stop   (index N)
    message_delta         (stop_reason == "tool_use")
    message_stop

:class:`AnthropicStreamState` tracks the running translation state across the
chunks of a single response (mirrors ``AnthropicStreamState`` in the
reverse-engineered ``copilot-api`` project).
"""

import json
from dataclasses import dataclass, field
from typing import Any

from src.thirdparty.anthropic_adapter import map_openai_stop_reason


@dataclass
class _ToolCallState:
    id: str
    name: str
    anthropic_block_index: int


@dataclass
class AnthropicStreamState:
    """Mutable state threaded through successive calls to :func:`translate_chunk`."""

    message_start_sent: bool = False
    content_block_index: int = 0
    content_block_open: bool = False
    tool_calls: dict[int, _ToolCallState] = field(default_factory=dict)


def _sse(event: dict[str, Any]) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


def _is_tool_block_open(state: AnthropicStreamState) -> bool:
    if not state.content_block_open:
        return False
    return any(
        tool_call.anthropic_block_index == state.content_block_index
        for tool_call in state.tool_calls.values()
    )


def _usage_from(chunk: dict[str, Any], *, include_output: bool) -> dict[str, Any]:
    usage = chunk.get("usage") or {}
    cached_tokens = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    usage_out: dict[str, Any] = {
        "input_tokens": usage.get("prompt_tokens", 0) - (cached_tokens or 0),
        "output_tokens": usage.get("completion_tokens", 0) if include_output else 0,
    }
    if cached_tokens is not None:
        usage_out["cache_read_input_tokens"] = cached_tokens
    return usage_out


def translate_chunk(chunk: dict[str, Any], state: AnthropicStreamState) -> list[str]:
    """Translate one Copilot chat-completion chunk into zero or more Anthropic SSE events.

    Mutates *state* in place so subsequent calls for the same response
    continue the same content-block/tool-call bookkeeping.
    """
    choices = chunk.get("choices") or []
    if not choices:
        return []

    choice = choices[0]
    delta = choice.get("delta") or {}
    events: list[dict[str, Any]] = []

    if not state.message_start_sent:
        events.append(
            {
                "type": "message_start",
                "message": {
                    "id": chunk.get("id", ""),
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": chunk.get("model", ""),
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": _usage_from(chunk, include_output=False),
                },
            }
        )
        state.message_start_sent = True

    content = delta.get("content")
    if content:
        if _is_tool_block_open(state):
            events.append({"type": "content_block_stop", "index": state.content_block_index})
            state.content_block_index += 1
            state.content_block_open = False
        if not state.content_block_open:
            events.append(
                {
                    "type": "content_block_start",
                    "index": state.content_block_index,
                    "content_block": {"type": "text", "text": ""},
                }
            )
            state.content_block_open = True
        events.append(
            {
                "type": "content_block_delta",
                "index": state.content_block_index,
                "delta": {"type": "text_delta", "text": content},
            }
        )

    for tool_call in delta.get("tool_calls") or []:
        tc_index = tool_call.get("index", 0)
        function = tool_call.get("function") or {}

        if tool_call.get("id") and function.get("name"):
            if state.content_block_open:
                events.append({"type": "content_block_stop", "index": state.content_block_index})
                state.content_block_index += 1
                state.content_block_open = False

            anthropic_index = state.content_block_index
            state.tool_calls[tc_index] = _ToolCallState(
                id=tool_call["id"], name=function["name"], anthropic_block_index=anthropic_index
            )
            events.append(
                {
                    "type": "content_block_start",
                    "index": anthropic_index,
                    "content_block": {
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": function["name"],
                        "input": {},
                    },
                }
            )
            state.content_block_open = True

        if function.get("arguments"):
            tool_state = state.tool_calls.get(tc_index)
            if tool_state is not None:
                events.append(
                    {
                        "type": "content_block_delta",
                        "index": tool_state.anthropic_block_index,
                        "delta": {"type": "input_json_delta", "partial_json": function["arguments"]},
                    }
                )

    finish_reason = choice.get("finish_reason")
    if finish_reason:
        if state.content_block_open:
            events.append({"type": "content_block_stop", "index": state.content_block_index})
            state.content_block_open = False
        events.append(
            {
                "type": "message_delta",
                "delta": {
                    "stop_reason": map_openai_stop_reason(finish_reason),
                    "stop_sequence": None,
                },
                "usage": _usage_from(chunk, include_output=True),
            }
        )
        events.append({"type": "message_stop"})

    return [_sse(event) for event in events]


def sse_error(message: str) -> str:
    """Return an Anthropic-shaped SSE ``error`` event."""
    return _sse({"type": "error", "error": {"type": "api_error", "message": message}})
