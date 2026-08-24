"""Convert Copilot SDK session events to Anthropic Messages API SSE format.

Anthropic SSE sequence for a streaming text response:

    message_start
    content_block_start  (index 0)
    content_block_delta* (text_delta)
    content_block_stop   (index 0)
    message_delta        (stop_reason, usage)
    message_stop

Anthropic SSE sequence for a streaming tool-use response (tool-use bridge):

    message_start
    content_block_start  (index N, content_block.type == "tool_use")
    content_block_delta  (input_json_delta, partial_json)
    content_block_stop   (index N)
    message_delta         (stop_reason == "tool_use")
    message_stop
"""

import json
from typing import Any


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


def sse_message_start(message_id: str, model: str) -> str:
    return _sse(
        {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }
    )


def sse_content_block_start(index: int = 0) -> str:
    return _sse(
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "text", "text": ""},
        }
    )


def sse_content_block_delta(text: str, index: int = 0) -> str:
    return _sse(
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "text_delta", "text": text},
        }
    )


def sse_content_block_stop(index: int = 0) -> str:
    return _sse({"type": "content_block_stop", "index": index})


def sse_message_delta(output_tokens: int = 0, stop_reason: str = "end_turn") -> str:
    return _sse(
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        }
    )


def sse_message_stop() -> str:
    return _sse({"type": "message_stop"})


def sse_error(error_type: str, message: str) -> str:
    return _sse({"type": "error", "error": {"type": error_type, "message": message}})


def sse_content_block_start_tool_use(tool_call_id: str, tool_name: str, index: int = 0) -> str:
    """Open a ``tool_use`` content block (tool-use bridge).

    Emitted when the Copilot SDK session raises an ``ExternalToolRequestedData``
    event for a bridged tool; the caller is expected to follow this with
    :func:`sse_content_block_delta_input_json` and
    :func:`sse_content_block_stop`, then end the turn with a
    ``message_delta`` carrying ``stop_reason="tool_use"``.
    """
    return _sse(
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "tool_use", "id": tool_call_id, "name": tool_name, "input": {}},
        }
    )


def sse_content_block_delta_input_json(partial_json: str, index: int = 0) -> str:
    """Emit (a chunk of) a tool_use block's JSON arguments.

    The Copilot SDK delivers a tool call's arguments as a single value
    rather than incremental deltas, so callers typically emit the entire
    JSON-encoded arguments in one call.
    """
    return _sse(
        {
            "type": "content_block_delta",
            "index": index,
            "delta": {"type": "input_json_delta", "partial_json": partial_json},
        }
    )
