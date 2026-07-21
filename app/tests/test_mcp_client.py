"""Tests for the MCP remote server client and tool integration."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from copilot.tools import ToolInvocation

from src.runtime.mcp_client import (
    MCPToolInfo,
    _content_to_dict,
    _get_input_schema,
    _is_error,
    call_mcp_tool,
    list_mcp_tools,
)
from src.runtime.tools import MCPToolArgs, build_mcp_tool_definitions, build_tools

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


# ---------------------------------------------------------------------------
# build_mcp_tool_definitions + isolation wrapper
# ---------------------------------------------------------------------------


def _make_mcp_tool_info(
    name: str = "echo_tool",
    description: str = "Echo the input",
    input_schema: dict[str, Any] | None = None,
) -> MCPToolInfo:
    return MCPToolInfo(
        name=name,
        description=description,
        input_schema=input_schema or {"type": "object", "properties": {"msg": {"type": "string"}}},
    )


def test_build_mcp_tool_definitions_produces_one_definition_per_tool() -> None:
    infos = [_make_mcp_tool_info("tool_a"), _make_mcp_tool_info("tool_b")]
    defs = build_mcp_tool_definitions(infos)
    assert [d.name for d in defs] == ["tool_a", "tool_b"]


def test_build_mcp_tool_definitions_sets_parameters_schema() -> None:
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    info = _make_mcp_tool_info(input_schema=schema)
    defs = build_mcp_tool_definitions([info])
    assert defs[0].parameters_schema == schema


def test_build_mcp_tool_definitions_uses_mcp_tool_args_model() -> None:
    defs = build_mcp_tool_definitions([_make_mcp_tool_info()])
    assert defs[0].params_model is MCPToolArgs


@pytest.mark.asyncio
async def test_mcp_tool_handler_proxies_call_to_mcp_server() -> None:
    """The built MCP tool definition should call the MCP server when invoked."""
    expected_result = {"content": [{"type": "text", "text": "ok"}]}
    info = _make_mcp_tool_info(name="echo_tool")

    # build_mcp_tool_definitions must be called INSIDE the patch so the closure
    # captures the mock rather than the real call_mcp_tool.
    with patch("src.runtime.mcp_client.call_mcp_tool", AsyncMock(return_value=expected_result)):
        defs = build_mcp_tool_definitions([info])
        handler = defs[0].handler

        result = await handler(
            MCPToolArgs.model_validate({"msg": "hello"}),
            ToolInvocation(
                session_id="s1",
                tool_call_id="c1",
                tool_name="echo_tool",
                arguments={"msg": "hello"},
            ),
        )

    assert result == expected_result


@pytest.mark.asyncio
async def test_mcp_tool_wrapped_contains_remote_exception() -> None:
    """Isolation wrapper must contain exceptions raised by the MCP server call."""
    import inspect
    from collections.abc import Awaitable
    from typing import cast

    from copilot.tools import ToolResult

    async def _boom(*_: Any, **__: Any) -> dict[str, Any]:
        raise RuntimeError("remote failure")

    # Build inside patch so the closure captures the mock that raises.
    with patch("src.runtime.mcp_client.call_mcp_tool", side_effect=_boom):
        info = _make_mcp_tool_info(name="fail_tool")
        defs = build_mcp_tool_definitions([info])
        tools = build_tools(defs, default_timeout_seconds=5.0)
        tool = tools[0]

        invocation = ToolInvocation(
            session_id="s2",
            tool_call_id="c2",
            tool_name="fail_tool",
            arguments={"msg": "x"},
        )
        raw = tool.handler(invocation)
        result: ToolResult
        if inspect.isawaitable(raw):
            result = await cast(Awaitable[ToolResult], raw)
        else:
            result = cast(ToolResult, raw)

    payload = json.loads(result.text_result_for_llm)
    assert result.result_type == "failure"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TOOL_EXECUTION_ERROR"


# ---------------------------------------------------------------------------
# MCPToolArgs model
# ---------------------------------------------------------------------------


def test_mcp_tool_args_accepts_any_extra_fields() -> None:
    args = MCPToolArgs.model_validate({"repo": "acme/app", "branch": "main", "dry_run": True})
    dumped = args.model_dump()
    assert dumped == {"repo": "acme/app", "branch": "main", "dry_run": True}


def test_mcp_tool_args_accepts_empty_dict() -> None:
    args = MCPToolArgs.model_validate({})
    assert args.model_dump() == {}

