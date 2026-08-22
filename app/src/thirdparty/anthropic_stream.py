"""Convert Copilot SDK session events to Anthropic Messages API SSE format.

Anthropic SSE sequence for a streaming text response:

    message_start
    content_block_start  (index 0)
    content_block_delta* (text_delta)
    content_block_stop   (index 0)
    message_delta        (stop_reason, usage)
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


def sse_message_delta(output_tokens: int = 0) -> str:
    return _sse(
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        }
    )


def sse_message_stop() -> str:
    return _sse({"type": "message_stop"})


def sse_error(error_type: str, message: str) -> str:
    return _sse({"type": "error", "error": {"type": error_type, "message": message}})
