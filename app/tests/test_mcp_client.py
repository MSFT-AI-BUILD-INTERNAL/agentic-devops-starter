"""Tests for the MCP remote server client (diagnostic tool listing only).

Note: MCP tool discovery/invocation for actual session use is no longer
implemented in application code — it is handled natively by the Copilot SDK
via ``mcp_servers=`` (see ``src.runtime.mcp_config``). This module's
``list_mcp_tools``/``call_mcp_tool`` remain only to back the standalone
``GET /v1/mcp/tools`` diagnostic endpoint.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.runtime.mcp_client import (
    _content_to_dict,
    _get_input_schema,
    _is_error,
    call_mcp_tool,
    list_mcp_tools,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transport_mock(read: Any = None, write: Any = None) -> AsyncMock:
    """Return an async context manager mock that yields (read, write)."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=(read or MagicMock(), write or MagicMock()))
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


def _make_session_mock(list_result: Any = None, call_result: Any = None) -> AsyncMock:
    """Return an async context manager mock wrapping a ClientSession."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    if list_result is not None:
        session.list_tools = AsyncMock(return_value=list_result)
    if call_result is not None:
        session.call_tool = AsyncMock(return_value=call_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


# ---------------------------------------------------------------------------
# list_mcp_tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_mcp_tools_returns_tool_infos() -> None:
    """list_mcp_tools should convert MCP Tool objects to MCPToolInfo instances."""
    fake_tool = MagicMock()
    fake_tool.name = "deploy_app"
    fake_tool.description = "Deploy an application"
    fake_tool.input_schema = {"type": "object", "properties": {"app_name": {"type": "string"}}}

    fake_result = MagicMock()
    fake_result.tools = [fake_tool]

    with (
        patch("src.runtime.mcp_client.streamable_http_client", return_value=_make_transport_mock()),
        patch("src.runtime.mcp_client.ClientSession", return_value=_make_session_mock(list_result=fake_result)),
    ):
        tools = await list_mcp_tools("https://example.com/mcp")

    assert len(tools) == 1
    assert tools[0].name == "deploy_app"
    assert tools[0].description == "Deploy an application"
    assert tools[0].input_schema == {
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
    }


@pytest.mark.asyncio
async def test_list_mcp_tools_returns_empty_on_connection_error() -> None:
    """list_mcp_tools should return [] without raising when the server is unreachable."""
    with patch(
        "src.runtime.mcp_client.streamable_http_client",
        side_effect=ConnectionError("refused"),
    ):
        tools = await list_mcp_tools("https://unreachable.example.com/mcp")

    assert tools == []


@pytest.mark.asyncio
async def test_list_mcp_tools_handles_missing_description() -> None:
    """list_mcp_tools should default to empty string when tool description is None."""
    fake_tool = MagicMock()
    fake_tool.name = "no_desc_tool"
    fake_tool.description = None
    fake_tool.input_schema = {}

    fake_result = MagicMock()
    fake_result.tools = [fake_tool]

    with (
        patch("src.runtime.mcp_client.streamable_http_client", return_value=_make_transport_mock()),
        patch("src.runtime.mcp_client.ClientSession", return_value=_make_session_mock(list_result=fake_result)),
    ):
        tools = await list_mcp_tools("https://example.com/mcp")

    assert tools[0].description == ""


# ---------------------------------------------------------------------------
# call_mcp_tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_mcp_tool_returns_content() -> None:
    """call_mcp_tool should return a dict with serialized content blocks."""
    fake_content = MagicMock()
    fake_content.model_dump = MagicMock(return_value={"type": "text", "text": "deployed!"})

    fake_result = MagicMock()
    fake_result.is_error = False
    fake_result.content = [fake_content]

    session_mock = _make_session_mock(call_result=fake_result)

    with (
        patch("src.runtime.mcp_client.streamable_http_client", return_value=_make_transport_mock()),
        patch("src.runtime.mcp_client.ClientSession", return_value=session_mock),
    ):
        result = await call_mcp_tool("https://example.com/mcp", "deploy_app", {"app_name": "myapp"})

    assert result == {"content": [{"type": "text", "text": "deployed!"}]}
    session_mock.call_tool.assert_called_once_with("deploy_app", {"app_name": "myapp"})


@pytest.mark.asyncio
async def test_call_mcp_tool_raises_on_error_response() -> None:
    """call_mcp_tool should raise RuntimeError when the MCP server signals is_error."""
    fake_result = MagicMock()
    fake_result.is_error = True
    fake_result.content = []

    with (
        patch("src.runtime.mcp_client.streamable_http_client", return_value=_make_transport_mock()),
        patch("src.runtime.mcp_client.ClientSession", return_value=_make_session_mock(call_result=fake_result)),
        pytest.raises(RuntimeError, match="error response"),
    ):
        await call_mcp_tool("https://example.com/mcp", "bad_tool", {})


# ---------------------------------------------------------------------------
# _get_input_schema helper
# ---------------------------------------------------------------------------


def test_get_input_schema_uses_snake_case_attribute() -> None:
    tool = MagicMock()
    tool.input_schema = {"type": "object"}
    assert _get_input_schema(tool) == {"type": "object"}


def test_get_input_schema_falls_back_to_camel_case() -> None:
    tool = MagicMock(spec=[])  # no attributes by default
    tool.inputSchema = {"type": "string"}
    # spec=[] means hasattr(tool, "input_schema") is False
    assert _get_input_schema(tool) == {"type": "string"}


def test_get_input_schema_returns_empty_dict_when_absent() -> None:
    tool = MagicMock(spec=[])
    assert _get_input_schema(tool) == {}


# ---------------------------------------------------------------------------
# _is_error helper
# ---------------------------------------------------------------------------


def test_is_error_uses_snake_case_attribute() -> None:
    result = MagicMock()
    result.is_error = True
    assert _is_error(result) is True


def test_is_error_falls_back_to_camel_case() -> None:
    result = MagicMock(spec=[])
    result.isError = True
    assert _is_error(result) is True


def test_is_error_returns_false_when_absent() -> None:
    result = MagicMock(spec=[])
    assert _is_error(result) is False


# ---------------------------------------------------------------------------
# _content_to_dict helper
# ---------------------------------------------------------------------------


def test_content_to_dict_uses_model_dump_when_available() -> None:
    obj = MagicMock()
    obj.model_dump = MagicMock(return_value={"type": "text", "text": "hi"})
    assert _content_to_dict(obj) == {"type": "text", "text": "hi"}


def test_content_to_dict_falls_back_to_str() -> None:
    assert _content_to_dict(42) == {"value": "42"}

