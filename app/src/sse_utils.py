"""Server-Sent Events (SSE) utilities for streaming responses."""

import base64
import json
import logging
from typing import Any

logger: logging.Logger | None = None


def set_logger(log_instance: logging.Logger) -> None:
    """Set the logger instance for this module."""
    global logger
    logger = log_instance


def sse_format(event: dict[str, Any]) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(event)}\n\n"


def build_prompt(
    messages: list[dict[str, str]], attachments: list[dict[str, Any]] | None = None
) -> str:
    """Extract the last user message content as the prompt, prepending file context if present."""
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        content = user_messages[-1].get("content", "")
    elif messages:
        content = messages[-1].get("content", "")
    else:
        content = ""

    if attachments:
        try:
            file_context = resolve_attachments(attachments)
        except Exception:
            if logger:
                logger.exception("Failed to resolve attachments for prompt")
            file_context = ""
        if file_context:
            content = file_context + "\n\n" + content

    return content


def resolve_attachments(attachments: list[dict[str, Any]]) -> str:
    """Download attached blobs and format as context for the AI prompt."""
    from src.blob_storage import get_blob_service

    parts: list[str] = []
    blob_service = get_blob_service()

    for att in attachments:
        blob_name = att.get("blob_name", "")
        original_filename = att.get("original_filename", "file")
        content_type = att.get("content_type", "")

        try:
            content = blob_service.download(blob_name)

            if content_type.startswith("text/") or content_type == "application/json":
                text = content.decode("utf-8", errors="replace")
                parts.append(f"[File: {original_filename}]\n{text}")
            else:
                encoded = base64.b64encode(content).decode("ascii")
                parts.append(
                    f"[File: {original_filename} ({content_type}, {len(content)} bytes, "
                    f"base64-encoded)]\n{encoded}"
                )
        except Exception:
            if logger:
                logger.exception("Failed to download attachment", extra={"blob_name": blob_name})
            parts.append(f"[File: {original_filename} — failed to load]")

    return "\n\n".join(parts)
