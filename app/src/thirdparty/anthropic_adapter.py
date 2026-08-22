"""Adapt Anthropic Messages API requests to Copilot SDK session input.

Phase 1 scope: text-only, single-user, no tools/images/thinking.
Unsupported features return explicit ValueError rather than silent loss.
"""

from typing import Any

from src.thirdparty.anthropic_models import AnthropicMessagesRequest

# Block types that are not supported in Phase 1.
_UNSUPPORTED_BLOCK_TYPES = frozenset({"tool_use", "tool_result", "image", "document", "thinking"})


def _extract_text(content: str | list[dict[str, Any]]) -> str:
    """Return plain text from an Anthropic content field (string or block list)."""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        block_type = block.get("type", "text")
        if block_type in _UNSUPPORTED_BLOCK_TYPES:
            raise ValueError(
                f"Unsupported content block type '{block_type}'. "
                "Only plain text content is supported in Phase 1."
            )
        if block_type == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def validate_request(request: AnthropicMessagesRequest) -> None:
    """Raise ValueError for unsupported request features (Phase 1).

    Returns without raising for supported requests.
    """
    if request.tools:
        raise ValueError(
            "Tool use is not supported by this adapter (Phase 1). "
            "Remove the 'tools' field from the request."
        )
    for msg in request.messages:
        if isinstance(msg.content, list):
            for block in msg.content:
                btype = block.get("type")
                if btype in _UNSUPPORTED_BLOCK_TYPES:
                    raise ValueError(
                        f"Unsupported content block type '{btype}' in messages. "
                        "Only plain text content is supported in Phase 1."
                    )


def extract_last_user_prompt(request: AnthropicMessagesRequest) -> str:
    """Return the text of the most recent user message.

    The Copilot SDK session maintains conversation history internally, so
    only the newest user message is sent per turn.
    """
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise ValueError("Request contains no user messages.")
    return _extract_text(user_messages[-1].content)


def extract_system_prompt(request: AnthropicMessagesRequest) -> str | None:
    """Return the system prompt as a plain string, or None if absent."""
    if request.system is None:
        return None
    if isinstance(request.system, str):
        return request.system or None
    parts: list[str] = []
    for block in request.system:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts) or None
