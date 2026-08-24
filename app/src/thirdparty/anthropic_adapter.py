"""Translate between the Anthropic Messages API and GitHub Copilot's OpenAI-shaped API.

This adapter is stateless: it has no notion of a server-side session or
conversation history. Each request is translated independently and the
caller's full ``messages`` history is forwarded to the Copilot API on every
call, exactly as Claude Code (or any other Anthropic Messages API client)
resends it. This mirrors the reverse-engineered ``copilot-api`` project
(https://github.com/ericc-ch/copilot-api), which this module's translation
logic is based on.
"""

import json
from typing import Any

from src.thirdparty.anthropic_models import AnthropicCountTokensRequest, AnthropicMessagesRequest

# Rough characters-per-token ratio used for the ``count_tokens`` approximation
# below. The adapter has no access to Anthropic's real tokenizer, so this is
# a best-effort estimate rather than an exact count.
_APPROX_CHARS_PER_TOKEN = 4

# Bounds for tool-definition parsing, to reject pathological requests outright.
MAX_TOOL_DEFINITIONS = 128
MAX_TOOL_NAME_LENGTH = 200

_OPENAI_TO_ANTHROPIC_STOP_REASON = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "end_turn",
}


def map_openai_stop_reason(finish_reason: str | None) -> str | None:
    """Map an OpenAI ``finish_reason`` to its Anthropic ``stop_reason`` equivalent."""
    if finish_reason is None:
        return None
    return _OPENAI_TO_ANTHROPIC_STOP_REASON.get(finish_reason, "end_turn")


def _normalize_model_name(model: str) -> str:
    """Strip Claude Code's dated sub-agent model suffixes Copilot doesn't recognize.

    e.g. ``claude-sonnet-4-20250514`` -> ``claude-sonnet-4``.
    """
    if model.startswith("claude-sonnet-4-"):
        return "claude-sonnet-4"
    if model.startswith("claude-opus-4-"):
        return "claude-opus-4"
    return model


def _extract_text(content: str | list[dict[str, Any]]) -> str:
    """Return plain text from an Anthropic content field (string or block list).

    Raises ValueError for unsupported block types so unsupported content
    (e.g. ``document``) isn't silently dropped. ``tool_use``/``tool_result``
    blocks are ignored here since they're translated elsewhere.
    """
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            raise ValueError("Content blocks must be JSON objects.")
        block_type = block.get("type", "text")
        if block_type == "text":
            text = block.get("text", "")
            if not isinstance(text, str):
                raise ValueError("Text content blocks must contain a string 'text' field.")
            parts.append(text)
        elif block_type == "thinking":
            parts.append(str(block.get("thinking", "")))
        elif block_type in ("tool_use", "tool_result"):
            continue
        else:
            raise ValueError(f"Unsupported content block type: '{block_type}'.")
    return "\n".join(parts)


def _map_content_for_openai(
    content: str | list[dict[str, Any]] | None,
) -> str | list[dict[str, Any]] | None:
    """Map an Anthropic content field to an OpenAI message ``content`` value.

    Text and thinking blocks are merged into plain text (OpenAI has no
    separate thinking block). When an image block is present, the content is
    instead returned as a list of OpenAI ``text``/``image_url`` parts so the
    image survives the translation.
    """
    if content is None:
        return None
    if isinstance(content, str):
        return content
    has_image = any(isinstance(block, dict) and block.get("type") == "image" for block in content)
    if not has_image:
        return _extract_text(content)

    parts: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, dict):
            raise ValueError("Content blocks must be JSON objects.")
        block_type = block.get("type")
        if block_type == "text":
            parts.append({"type": "text", "text": block.get("text", "")})
        elif block_type == "thinking":
            parts.append({"type": "text", "text": block.get("thinking", "")})
        elif block_type == "image":
            source = block.get("source") or {}
            media_type = source.get("media_type", "image/png")
            data = source.get("data", "")
            parts.append(
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}
            )
        elif block_type in ("tool_use", "tool_result"):
            continue
        else:
            raise ValueError(f"Unsupported content block type: '{block_type}'.")
    return parts


def _handle_user_message(content: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate one Anthropic user message into one or more OpenAI messages.

    ``tool_result`` blocks become standalone OpenAI ``tool`` messages (which
    must precede the remaining user content to preserve the
    tool_use -> tool_result -> user ordering OpenAI expects); any other
    content becomes a single ``user`` message.
    """
    if not isinstance(content, list):
        return [{"role": "user", "content": _map_content_for_openai(content)}]

    tool_results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
    other_blocks = [b for b in content if not (isinstance(b, dict) and b.get("type") == "tool_result")]

    messages: list[dict[str, Any]] = []
    for block in tool_results:
        result_content = block.get("content", "")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": block.get("tool_use_id", ""),
                "content": _map_content_for_openai(result_content),
            }
        )
    if other_blocks:
        messages.append({"role": "user", "content": _map_content_for_openai(other_blocks)})
    return messages


def _validate_tool_use_block(block: dict[str, Any]) -> dict[str, Any]:
    """Validate a ``tool_use`` block's required fields, raising ValueError if malformed."""
    tool_id = block.get("id")
    if not isinstance(tool_id, str) or not tool_id.strip():
        raise ValueError("tool_use blocks must have a non-empty 'id'.")
    name = block.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool_use blocks must have a non-empty 'name'.")
    tool_input = block.get("input", {})
    if not isinstance(tool_input, dict):
        raise ValueError("tool_use blocks must have an 'input' that is a JSON object.")
    return {
        "id": tool_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(tool_input),
        },
    }


def _handle_assistant_message(content: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate one Anthropic assistant message into one OpenAI message.

    ``tool_use`` blocks become OpenAI ``tool_calls``; text/thinking blocks are
    merged into the message's ``content``.
    """
    if not isinstance(content, list):
        return [{"role": "assistant", "content": _map_content_for_openai(content)}]

    tool_use_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    text_content = _map_content_for_openai(content)

    if not tool_use_blocks:
        return [{"role": "assistant", "content": text_content}]

    return [
        {
            "role": "assistant",
            "content": text_content or None,
            "tool_calls": [_validate_tool_use_block(block) for block in tool_use_blocks],
        }
    ]


def _translate_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Validate and translate Anthropic ``tools`` into OpenAI ``tools``.

    Raises ValueError for malformed tool declarations -- missing/blank name,
    a duplicate name, or too many declared tools -- so callers can return an
    explicit 400 instead of silently forwarding a broken tool list.
    """
    if not tools:
        return None
    if len(tools) > MAX_TOOL_DEFINITIONS:
        raise ValueError(f"Too many tools declared ({len(tools)}); the limit is {MAX_TOOL_DEFINITIONS}.")

    translated: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for raw in tools:
        if not isinstance(raw, dict):
            raise ValueError("Each tool definition must be a JSON object.")
        name = str(raw.get("name", "")).strip()
        if not name:
            raise ValueError("Tool definitions must have a non-empty 'name'.")
        if len(name) > MAX_TOOL_NAME_LENGTH:
            raise ValueError(f"Tool name '{name[:40]}...' exceeds {MAX_TOOL_NAME_LENGTH} characters.")
        if name in seen_names:
            raise ValueError(f"Duplicate tool name '{name}'.")
        seen_names.add(name)
        translated.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": raw.get("description", ""),
                    "parameters": raw.get("input_schema") or {},
                },
            }
        )
    return translated


def _translate_tool_choice(tool_choice: dict[str, Any] | None) -> Any:
    """Translate an Anthropic ``tool_choice`` into its OpenAI equivalent."""
    if not tool_choice:
        return None
    choice_type = tool_choice.get("type")
    if choice_type == "auto":
        return "auto"
    if choice_type == "any":
        return "required"
    if choice_type == "none":
        return "none"
    if choice_type == "tool":
        name = tool_choice.get("name")
        if name:
            return {"type": "function", "function": {"name": name}}
    return None


def translate_to_openai(request: AnthropicMessagesRequest) -> dict[str, Any]:
    """Translate a validated Anthropic Messages request into a Copilot chat-completions payload."""
    messages: list[dict[str, Any]] = []

    system_prompt = extract_system_prompt(request)
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for message in request.messages:
        if message.role == "user":
            messages.extend(_handle_user_message(message.content))
        else:
            messages.extend(_handle_assistant_message(message.content))

    payload: dict[str, Any] = {
        "model": _normalize_model_name(request.model),
        "messages": messages,
        "max_tokens": request.max_tokens,
        "stream": request.stream,
    }
    if request.stop_sequences:
        payload["stop"] = request.stop_sequences
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    user_id = (request.metadata or {}).get("user_id")
    if user_id:
        payload["user"] = user_id

    tools = _translate_tools(request.tools)
    if tools:
        payload["tools"] = tools
    tool_choice = _translate_tool_choice(request.tool_choice)
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    return payload


def translate_to_anthropic(response: dict[str, Any]) -> dict[str, Any]:
    """Translate a non-streaming Copilot chat-completions response into an Anthropic response body."""
    text_blocks: list[dict[str, Any]] = []
    tool_use_blocks: list[dict[str, Any]] = []
    stop_reason: str | None = None

    for choice in response.get("choices", []):
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content:
            text_blocks.append({"type": "text", "text": content})

        for tool_call in message.get("tool_calls") or []:
            function = tool_call.get("function") or {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except (TypeError, ValueError):
                arguments = {}
            tool_use_blocks.append(
                {
                    "type": "tool_use",
                    "id": tool_call.get("id", ""),
                    "name": function.get("name", ""),
                    "input": arguments,
                }
            )

        finish_reason = choice.get("finish_reason")
        if finish_reason == "tool_calls" or stop_reason in (None, "stop"):
            stop_reason = finish_reason

    usage = response.get("usage") or {}
    cached_tokens = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    usage_out: dict[str, Any] = {
        "input_tokens": usage.get("prompt_tokens", 0) - (cached_tokens or 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }
    if cached_tokens is not None:
        usage_out["cache_read_input_tokens"] = cached_tokens

    return {
        "id": response.get("id", ""),
        "type": "message",
        "role": "assistant",
        "model": response.get("model", ""),
        "content": [*text_blocks, *tool_use_blocks],
        "stop_reason": map_openai_stop_reason(stop_reason),
        "stop_sequence": None,
        "usage": usage_out,
    }


def extract_system_prompt(request: AnthropicMessagesRequest) -> str | None:
    """Return the request's system prompt as plain text, if any."""
    if request.system is None:
        return None
    text = request.system if isinstance(request.system, str) else _extract_text(request.system)
    return text or None


def _approximate_content_length(content: str | list[dict[str, Any]]) -> int:
    """Return a best-effort character count for a content field.

    Unlike :func:`_extract_text`, this never raises for unsupported block
    types; it falls back to the block's raw JSON size so ``count_tokens``
    still returns a reasonable estimate instead of a hard failure.
    """
    if isinstance(content, str):
        return len(content)
    total = 0
    for block in content:
        block_type = block.get("type", "text") if isinstance(block, dict) else "text"
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
