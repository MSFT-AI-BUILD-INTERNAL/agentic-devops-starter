"""Adapt Anthropic Messages API requests to Copilot SDK session input.

The adapter supports text-only requests and parses tool-use bridge requests;
images, documents, and thinking blocks remain unsupported.
Unsupported features return explicit ValueError rather than silent loss.

Tool-use bridge support (parsing/validation of ``tools`` and ``tool_result``
content blocks) lives alongside the Phase 1 helpers below; it is additive and
does not change the behavior of ``validate_request``/``extract_last_user_prompt``,
which still reject tool content so existing text-only callers are unaffected.
See :mod:`src.thirdparty.anthropic_tool_bridge` for the pending-call state and
SDK tool adapters that make use of these parsed values.
"""

from typing import Any

from src.thirdparty.anthropic_models import (
    AnthropicCountTokensRequest,
    AnthropicMessagesRequest,
    AnthropicToolDefinition,
    AnthropicToolResultBlock,
)

# Rough characters-per-token ratio used for the ``count_tokens`` approximation
# below. The adapter has no access to Anthropic's real tokenizer, so this is
# a best-effort estimate rather than an exact count.
_APPROX_CHARS_PER_TOKEN = 4

# Block types that are not supported in Phase 1.
_UNSUPPORTED_BLOCK_TYPES = frozenset({"tool_use", "tool_result", "image", "document", "thinking"})

# Bounds for tool-use bridge parsing, to reject pathological requests outright
# rather than building an unbounded number of SDK tool registrations.
MAX_TOOL_DEFINITIONS = 128
MAX_TOOL_NAME_LENGTH = 200


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
    return _extract_text(request.system) or None


def _approximate_content_length(content: str | list[dict[str, Any]]) -> int:
    """Return a best-effort character count for a content field.

    Unlike :func:`_extract_text`, this never raises for content block types
    the adapter doesn't otherwise support (tool use, images, ...); it falls
    back to the block's raw JSON size so ``count_tokens`` still returns a
    reasonable estimate instead of a hard failure.
    """
    if isinstance(content, str):
        return len(content)
    total = 0
    for block in content:
        block_type = block.get("type", "text")
        if block_type == "text":
            total += len(block.get("text", ""))
        else:
            total += len(str(block))
    return total


def estimate_input_tokens(request: AnthropicCountTokensRequest) -> int:
    """Return an approximate input token count for a count_tokens request.

    The adapter has no access to Anthropic's real tokenizer, so this uses a
    simple characters-per-token heuristic across the system prompt and all
    messages. An approximation is preferable to omitting the endpoint
    entirely, since Claude Code calls it during normal operation.
    """
    total_chars = 0
    if request.system is not None:
        total_chars += _approximate_content_length(request.system)
    for msg in request.messages:
        total_chars += _approximate_content_length(msg.content)
    if request.tools:
        total_chars += len(str(request.tools))
    return max(1, total_chars // _APPROX_CHARS_PER_TOKEN)


def parse_tool_definitions(request: AnthropicMessagesRequest) -> list[AnthropicToolDefinition]:
    """Validate and parse ``request.tools`` into typed tool definitions.

    This is separate from :func:`validate_request`, which still rejects any
    request carrying ``tools`` so existing text-only callers keep their
    current behavior; callers that opt into the tool-use bridge should call
    this instead of (or before enabling) ``validate_request``.

    Raises ValueError for malformed tool declarations -- missing/blank name,
    a duplicate name, a non-object ``input_schema``, or too many declared
    tools -- so callers can return an explicit 400 instead of silently
    dropping or mis-registering a tool.
    """
    if not request.tools:
        return []
    if len(request.tools) > MAX_TOOL_DEFINITIONS:
        raise ValueError(
            f"Too many tools declared ({len(request.tools)}); "
            f"the limit is {MAX_TOOL_DEFINITIONS}."
        )
    definitions: list[AnthropicToolDefinition] = []
    seen_names: set[str] = set()
    for raw in request.tools:
        try:
            definition = AnthropicToolDefinition.model_validate(raw)
        except Exception as exc:
            raise ValueError(f"Invalid tool definition: {exc}") from exc
        name = definition.name.strip()
        if not name:
            raise ValueError("Tool definitions must have a non-empty 'name'.")
        if len(name) > MAX_TOOL_NAME_LENGTH:
            raise ValueError(
                f"Tool name '{name[:40]}...' exceeds {MAX_TOOL_NAME_LENGTH} characters."
            )
        if name in seen_names:
            raise ValueError(f"Duplicate tool name '{name}'.")
        schema_type = definition.input_schema.get("type") if definition.input_schema else None
        if schema_type not in (None, "object"):
            raise ValueError(f"Tool '{name}' input_schema must describe a JSON object.")
        seen_names.add(name)
        definitions.append(definition)
    return definitions


def extract_tool_result_blocks(request: AnthropicMessagesRequest) -> list[AnthropicToolResultBlock]:
    """Return every ``tool_result`` content block across all request messages.

    Claude Code sends tool results as a new user message following a
    ``tool_use`` turn. Results are collected across *all* messages (not just
    the last one) so batched/parallel tool calls resolved out of order are
    still found.
    """
    blocks: list[AnthropicToolResultBlock] = []
    for msg in request.messages:
        if not isinstance(msg.content, list):
            continue
        for raw_block in msg.content:
            if not isinstance(raw_block, dict) or raw_block.get("type") != "tool_result":
                continue
            try:
                blocks.append(AnthropicToolResultBlock.model_validate(raw_block))
            except Exception as exc:
                raise ValueError(f"Invalid tool_result block: {exc}") from exc
    return blocks
