"""MCP (Model Context Protocol) remote server client.

Provides functions to discover and call tools on a remote MCP server via the
Streamable HTTP transport.  The server URL is configured via ``MCP_SERVER_URL``
(or ``COPILOT_API_MCP_SERVER_URL``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.core.config import settings
from src.core.logging_utils import setup_logging

logger = setup_logging(settings.log_level)


@dataclass(frozen=True)
class MCPToolInfo:
    """Metadata for a tool discovered from the remote MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


async def list_mcp_tools(url: str) -> list[MCPToolInfo]:
    """Connect to the MCP server and return the full tool list.

    Returns an empty list when the server is unreachable or returns no tools.
    """
    try:
        async with streamable_http_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = [
                    MCPToolInfo(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=_get_input_schema(tool),
                    )
                    for tool in result.tools
                ]
                logger.info(
                    "MCP tools discovered",
                    extra={
                        "mcp_server_url": url,
                        "tool_count": len(tools),
                        "tool_names": [t.name for t in tools],
                    },
                )
                return tools
    except Exception as exc:
        logger.warning(
            "MCP tool listing failed — no MCP tools will be registered",
            extra={"mcp_server_url": url, "error": str(exc)},
        )
        return []


async def call_mcp_tool(
    url: str, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call a tool on the remote MCP server and return its result payload.

    Raises :class:`RuntimeError` when the MCP server signals an error response.
    """
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if _is_error(result):
                raise RuntimeError(f"MCP tool '{tool_name}' returned an error response")
            return {
                "content": [_content_to_dict(block) for block in result.content],
            }


def _get_input_schema(tool: Any) -> dict[str, Any]:
    """Extract the input schema from an MCP Tool object.

    Handles both the 1.x API (``inputSchema``) and the 2.x API (``input_schema``).
    """
    if hasattr(tool, "input_schema"):
        schema = tool.input_schema
    elif hasattr(tool, "inputSchema"):
        schema = tool.inputSchema
    else:
        schema = {}
    return schema if isinstance(schema, dict) else {}


def _is_error(result: Any) -> bool:
    """Return whether the MCP call result signals an error.

    Handles both the 1.x API (``isError``) and the 2.x API (``is_error``).
    """
    if hasattr(result, "is_error"):
        return bool(result.is_error)
    if hasattr(result, "isError"):
        return bool(result.isError)
    return False


def _content_to_dict(content: Any) -> dict[str, Any]:
    """Serialize an MCP content block to a plain dict."""
    if hasattr(content, "model_dump"):
        return content.model_dump()
    if hasattr(content, "__dict__"):
        return dict(vars(content))
    return {"value": str(content)}
