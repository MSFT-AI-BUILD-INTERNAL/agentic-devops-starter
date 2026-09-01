"""Tests for SDK-native MCP server configuration."""

from __future__ import annotations

from copilot.generated.rpc import MCPServerConfig, MCPServerConfigType

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
    assert isinstance(server, MCPServerConfig)
    assert server.url == "https://example.com/mcp"
    assert server.type == MCPServerConfigType.HTTP
