"""Tests for code-based tool registration and isolation boundaries."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Generator
from typing import cast

import pytest
from copilot.tools import Tool, ToolInvocation, ToolResult
from pydantic import BaseModel, Field

import src.runtime.tools as tools_module
from src.runtime.tools import ToolDefinition, build_tools, get_registered_tools


@pytest.fixture(autouse=True)
def reset_tool_cache() -> Generator[None, None, None]:
    tools_module._registered_tools = []
    tools_module._registered_tool_names = []
    yield
    tools_module._registered_tools = []
    tools_module._registered_tool_names = []


async def _invoke(tool: Tool, invocation: ToolInvocation) -> ToolResult:
    result = tool.handler(invocation)
    if inspect.isawaitable(result):
        return await cast(Awaitable[ToolResult], result)
    return cast(ToolResult, result)


@pytest.mark.asyncio
async def test_deterministic_tool_returns_structured_success() -> None:
    tools = {tool.name: tool for tool in get_registered_tools()}
    invocation = ToolInvocation(
        session_id="session-1",
        tool_call_id="call-1",
        tool_name="transform_text",
        arguments={"text": "  hello world  ", "uppercase": True},
    )

    result = await _invoke(tools["transform_text"], invocation)
    payload = json.loads(result.text_result_for_llm)

    assert result.result_type == "success"
    assert payload["ok"] is True
    assert payload["data"]["transformed_text"] == "HELLO WORLD"


@pytest.mark.asyncio
async def test_tool_wrapper_rejects_invalid_arguments() -> None:
    tools = {tool.name: tool for tool in get_registered_tools()}
    invocation = ToolInvocation(
        session_id="session-2",
        tool_call_id="call-2",
        tool_name="transform_text",
        arguments={"uppercase": True},
    )

    result = await _invoke(tools["transform_text"], invocation)
    payload = json.loads(result.text_result_for_llm)

    assert result.result_type == "failure"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"


class _FailingParams(BaseModel):
    message: str = Field(min_length=1)


async def _always_fail(_params: BaseModel, _invocation: ToolInvocation) -> dict[str, str]:
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_tool_wrapper_contains_unexpected_exceptions() -> None:
    wrapped_tool = build_tools(
        [
            ToolDefinition(
                name="always_fail",
                description="Fails intentionally",
                params_model=_FailingParams,
                handler=_always_fail,
            )
        ],
        default_timeout_seconds=1.0,
    )[0]
    invocation = ToolInvocation(
        session_id="session-3",
        tool_call_id="call-3",
        tool_name="always_fail",
        arguments={"message": "x"},
    )

    result = await _invoke(wrapped_tool, invocation)
    payload = json.loads(result.text_result_for_llm)

    assert result.result_type == "failure"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TOOL_EXECUTION_ERROR"


class _SlowParams(BaseModel):
    wait_seconds: float = Field(default=0.2, ge=0.0)


async def _slow_tool(params: BaseModel, _invocation: ToolInvocation) -> dict[str, float]:
    typed = _SlowParams.model_validate(params.model_dump())
    await asyncio.sleep(typed.wait_seconds)
    return {"slept": typed.wait_seconds}


@pytest.mark.asyncio
async def test_tool_wrapper_enforces_timeout() -> None:
    wrapped_tool = build_tools(
        [
            ToolDefinition(
                name="slow_tool",
                description="Sleeps longer than timeout",
                params_model=_SlowParams,
                handler=_slow_tool,
                timeout_seconds=0.01,
            )
        ],
        default_timeout_seconds=1.0,
    )[0]
    invocation = ToolInvocation(
        session_id="session-4",
        tool_call_id="call-4",
        tool_name="slow_tool",
        arguments={"wait_seconds": 0.1},
    )

    result = await _invoke(wrapped_tool, invocation)
    payload = json.loads(result.text_result_for_llm)

    assert result.result_type == "failure"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "TOOL_TIMEOUT"


def _sync_handler(_params: BaseModel, _invocation: ToolInvocation) -> dict[str, str]:
    return {"result": "ok"}


def test_build_tool_rejects_sync_handler() -> None:
    definition = ToolDefinition(
        name="sync_tool",
        description="Sync handler that must be rejected",
        params_model=_FailingParams,
        handler=_sync_handler,  # type: ignore[arg-type]
    )

    with pytest.raises(TypeError, match="must be an async function"):
        build_tools([definition], default_timeout_seconds=1.0)


def test_tool_registry_rejects_duplicate_names() -> None:
    definitions = [
        ToolDefinition(
            name="duplicate_name",
            description="first",
            params_model=_FailingParams,
            handler=_always_fail,
        ),
        ToolDefinition(
            name="duplicate_name",
            description="second",
            params_model=_FailingParams,
            handler=_always_fail,
        ),
    ]

    with pytest.raises(RuntimeError, match="Duplicate tool names are not allowed"):
        build_tools(definitions, default_timeout_seconds=1.0)
