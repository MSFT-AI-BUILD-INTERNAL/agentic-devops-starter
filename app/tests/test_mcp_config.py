"""Tests for SDK-native MCP server configuration."""

from __future__ import annotations

from src.core.config import settings
from src.runtime.mcp_config import build_mcp_servers_config


def test_build_mcp_servers_config_returns_none_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_server_url", "")
    assert build_mcp_servers_config() is None


def test_build_mcp_servers_config_returns_http_server_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mcp_server_url", "https://example.com/mcp")

    result = build_mcp_servers_config()

    assert result is not None
    assert list(result.keys()) == ["remote"]
    server = result["remote"]
    # Must be a plain JSON-serializable dict (via MCPServerConfig.to_dict()),
    # not an MCPServerConfig dataclass instance: CopilotClient.create_session
    # forwards this mapping verbatim into the outbound JSON-RPC payload
    # without dataclass conversion, so passing the dataclass itself makes
    # every session creation fail with a JSON serialization TypeError.
    assert isinstance(server, dict)
    # ``tools`` must be present explicitly: the CLI's wire schema
    # (MCPHTTPServerConfig) treats it as a required key, not optional as the
    # MCPServerConfig dataclass docstring suggests — omitting it causes the
    # CLI to report the server as "not_configured" without attempting a
    # connection at all (observed in production via the
    # SessionMcpServersLoadedData event).
    assert server == {
        "type": "http",
        "url": "https://example.com/mcp",
        "tools": ["*"],
    }

    import json

    json.dumps(result)  # must not raise
