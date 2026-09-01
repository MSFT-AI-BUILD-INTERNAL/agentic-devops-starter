"""SDK tool allow/deny policy for Copilot sessions.

Builds the ``available_tools`` / ``excluded_tools`` entries attached to
``session_kwargs`` before a session is created or resumed. Also owns the
(cached) lookup of tool names exposed by the remote MCP server, needed so an
``available_tools`` allowlist can still admit SDK-native MCP tools (see
:func:`_get_remote_mcp_tool_names` for why this lookup is necessary at all).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from src.core.config import settings
from src.core.logging_utils import setup_logging

logger = setup_logging(settings.log_level)

# Cache of tool names discovered from the remote MCP server (see
# ``_get_remote_mcp_tool_names``). ``None`` means "not yet fetched"; an empty
# list is a valid cached result (server unreachable or has no tools).
_mcp_tool_names_cache: list[str] | None = None
_mcp_tool_names_lock = asyncio.Lock()

# Built-in SDK tools that expose the host filesystem, shell, or local database.
# These are unsafe to offer when the Copilot SDK is served as a public web
# service and are excluded from every session by default.
_WEB_UNSAFE_TOOLS: tuple[str, ...] = (
    "bash",
    "write_bash",
    "read_bash",
    "stop_bash",
    "list_bash",
    "view",
    "create",
    "edit",
    "grep",
    "glob",
    "sql",
)


def _get_allowed_tools() -> list[str] | None:
    """Return optional SDK tool allowlist from COPILOT_API_ALLOWED_TOOLS."""
    value = os.environ.get("COPILOT_API_ALLOWED_TOOLS")
    if value is None:
        return None

    non_empty_tools = [tool.strip() for tool in value.split(",") if tool.strip()]
    return non_empty_tools or None


def get_excluded_tools() -> list[str] | None:
    """Return the SDK tool denylist applied to every session.

    Controlled by ``COPILOT_API_EXCLUDED_TOOLS`` (comma-separated). When the
    variable is unset the filesystem/shell/database tools in
    :data:`_WEB_UNSAFE_TOOLS` are excluded by default (secure-by-default). A
    blank value explicitly disables the denylist.

    Note: the SDK ignores ``excluded_tools`` whenever an ``available_tools``
    allowlist is also supplied, so the two must not be combined.
    """
    value = os.environ.get("COPILOT_API_EXCLUDED_TOOLS")
    if value is None:
        return list(_WEB_UNSAFE_TOOLS)

    names = [tool.strip() for tool in value.split(",") if tool.strip()]
    return names or None


async def _get_remote_mcp_tool_names() -> list[str]:
    """Return tool names exposed by the remote MCP server, cached for the process.

    The Copilot SDK owns MCP tool discovery/invocation natively (registered via
    ``mcp_servers=`` — see :mod:`src.runtime.mcp_config`), but it does not
    currently expose an API to read back the tool names it discovered for a
    session. To let an ``available_tools`` allowlist (``COPILOT_API_ALLOWED_TOOLS``)
    still admit those SDK-native MCP tools, we independently query the remote
    MCP server's standard ``tools/list`` (the same call already used by the
    ``GET /v1/mcp/tools`` diagnostic endpoint) and cache the result.

    Requires no changes to the remote MCP server. The cache is populated once
    per process and is not refreshed if the remote tool set changes later;
    restart the process (or clear ``_mcp_tool_names_cache``) to pick up
    changes. Failures are non-fatal: an empty list is cached and a warning is
    logged, matching the previous ``load_tools()`` behavior.
    """
    global _mcp_tool_names_cache

    if not settings.mcp_server_url:
        return []

    if _mcp_tool_names_cache is not None:
        return _mcp_tool_names_cache

    async with _mcp_tool_names_lock:
        if _mcp_tool_names_cache is not None:
            return _mcp_tool_names_cache

        from src.runtime.mcp_client import list_mcp_tools

        tool_infos = await list_mcp_tools(settings.mcp_server_url)
        _mcp_tool_names_cache = [info.name for info in tool_infos]
        return _mcp_tool_names_cache


async def apply_tool_policy(session_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Attach the SDK tool allow/deny policy to *session_kwargs* in place.

    An ``available_tools`` allowlist takes precedence: when configured, the
    SDK ignores ``excluded_tools``, so we only apply one of the two.
    """
    allowed_tools = _get_allowed_tools()
    if allowed_tools is not None:
        # Keep runtime-registered custom tools visible even when a built-in
        # SDK allowlist is configured.
        available_tools = list(allowed_tools)
        for tool in session_kwargs.get("tools", []):
            tool_name = getattr(tool, "name", "")
            if isinstance(tool_name, str) and tool_name and tool_name not in available_tools:
                available_tools.append(tool_name)

        # Also admit tools from the remote MCP server registered natively via
        # ``mcp_servers=``: the SDK discovers/invokes them itself and they
        # never appear in session_kwargs["tools"], so without this they'd be
        # silently filtered out by the allowlist.
        for tool_name in await _get_remote_mcp_tool_names():
            if tool_name not in available_tools:
                available_tools.append(tool_name)

        session_kwargs["available_tools"] = available_tools
        return session_kwargs

    excluded_tools = get_excluded_tools()
    if excluded_tools is not None:
        session_kwargs["excluded_tools"] = excluded_tools
    return session_kwargs
