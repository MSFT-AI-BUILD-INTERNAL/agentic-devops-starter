"""SDK-native MCP server configuration.

Builds the ``mcp_servers`` mapping passed to ``CopilotClient.create_session``/
``resume_session``. The GitHub Copilot SDK owns MCP tool discovery, refresh,
and invocation natively when a server is registered this way — the
application no longer needs to open its own MCP client connection, poll
``tools/list``, or proxy tool calls itself.
"""

from __future__ import annotations

from copilot.generated.rpc import MCPServerConfig, MCPServerConfigType

from src.core.config import settings

# Stable key under which the configured remote MCP server is registered with
# the SDK. Used as the dict key in the ``mcp_servers`` payload.
_MCP_SERVER_NAME = "remote"


def build_mcp_servers_config() -> dict[str, MCPServerConfig] | None:
    """Return the SDK ``mcp_servers`` mapping, or ``None`` when unconfigured.

    When ``settings.mcp_server_url`` is set, the SDK connects to it natively
    over Streamable HTTP, discovers its tools, keeps that list current across
    the session's lifetime, and proxies tool calls itself — none of that is
    reimplemented here.
    """
    if not settings.mcp_server_url:
        return None

    return {
        _MCP_SERVER_NAME: MCPServerConfig(
            url=settings.mcp_server_url,
            type=MCPServerConfigType.HTTP,
        ),
    }
