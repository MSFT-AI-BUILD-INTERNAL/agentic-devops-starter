"""Code-based Copilot SDK tool registration with isolation and timeout boundaries."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast
from urllib.error import URLError
from urllib.request import Request, urlopen

from copilot.tools import Tool, ToolInvocation, ToolResult
from pydantic import BaseModel, Field, ValidationError

from src.core.config import settings
from src.core.logging_utils import correlation_id, new_correlation_id, setup_logging

logger = setup_logging(settings.log_level)


class ExternalDependencyUnavailableError(RuntimeError):
    """Raised when an external dependency cannot be reached."""


@dataclass(frozen=True)
class ToolDefinition:
    """Definition for a code-based Copilot tool."""

    name: str
    description: str
    params_model: type[BaseModel]
    handler: Callable[[BaseModel, ToolInvocation], Awaitable[Any]]
    timeout_seconds: float | None = None
    skip_permission: bool = False


class TransformTextArgs(BaseModel):
    """Input arguments for the deterministic text transform tool."""

    text: str = Field(min_length=1, description="Text to transform.")
    uppercase: bool = Field(default=False, description="Whether to convert to uppercase.")
    strip_whitespace: bool = Field(default=True, description="Whether to trim outer whitespace.")


class FetchGitHubZenArgs(BaseModel):
    """Input arguments for the external API example tool."""

    max_length: int = Field(
        default=120,
        ge=1,
        le=300,
        description="Maximum response length returned to the model.",
    )


def _encode_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _validation_issues(error: ValidationError) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for issue in error.errors():
        location = ".".join(str(part) for part in issue.get("loc", ()))
        issues.append({"field": location or "root", "message": issue.get("msg", "Invalid value")})
    return issues


async def _transform_text(params: BaseModel, _invocation: ToolInvocation) -> dict[str, Any]:
    typed_params = TransformTextArgs.model_validate(params.model_dump())
    value = typed_params.text
    if typed_params.strip_whitespace:
        value = value.strip()
    if typed_params.uppercase:
        value = value.upper()
    return {"transformed_text": value}


def _fetch_remote_text(url: str, timeout_seconds: float) -> str:
    request = Request(
        url=url,
        headers={
            "Accept": "text/plain",
            "User-Agent": "agentic-devops-starter-tool/1.0",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = cast(bytes, response.read(2048))
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace").strip()


async def _fetch_github_zen(params: BaseModel, _invocation: ToolInvocation) -> dict[str, Any]:
    typed_params = FetchGitHubZenArgs.model_validate(params.model_dump())
    timeout_seconds = max(0.1, min(settings.tool_timeout, 15.0))
    try:
        text = await asyncio.to_thread(
            _fetch_remote_text,
            settings.tool_external_api_url,
            timeout_seconds,
        )
    except (TimeoutError, URLError, OSError) as exc:
        raise ExternalDependencyUnavailableError("dependency unavailable") from exc
    return {"message": text[: typed_params.max_length]}


def _build_base_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="transform_text",
            description="Deterministic text transformation helper for trim/uppercase operations.",
            params_model=TransformTextArgs,
            handler=_transform_text,
        ),
        ToolDefinition(
            name="fetch_github_zen",
            description="Fetches a short text response from GitHub's public zen endpoint.",
            params_model=FetchGitHubZenArgs,
            handler=_fetch_github_zen,
            timeout_seconds=6.0,
        ),
    ]


def build_tool(definition: ToolDefinition, default_timeout_seconds: float) -> Tool:
    """Build a Copilot SDK tool wrapped by a safety boundary."""
    if not inspect.iscoroutinefunction(definition.handler):
        raise TypeError(
            f"Tool handler for '{definition.name}' must be an async function. "
            "Synchronous handlers cannot be reliably cancelled on timeout and may exhaust the thread pool."
        )

    async def wrapped_handler(invocation: ToolInvocation) -> ToolResult:
        started = time.monotonic()
        timeout_seconds = definition.timeout_seconds or default_timeout_seconds
        session_id = invocation.session_id or "unknown-session"
        tool_call_id = invocation.tool_call_id or "unknown-call"
        current_correlation = correlation_id.get("")
        generated_correlation = not bool(current_correlation)
        if generated_correlation:
            current_correlation = new_correlation_id()

        logger.info(
            "Tool invocation started",
            extra={
                "tool_name": definition.name,
                "tool_call_id": tool_call_id,
                "session_id": session_id,
                "timeout_seconds": timeout_seconds,
            },
        )
        try:
            validated = definition.params_model.model_validate(invocation.arguments or {})
            result_payload = await asyncio.wait_for(
                definition.handler(validated, invocation),
                timeout=timeout_seconds,
            )

            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Tool invocation completed",
                extra={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "outcome": "success",
                    "duration_ms": duration_ms,
                },
            )
            return ToolResult(
                text_result_for_llm=_encode_result(
                    {
                        "ok": True,
                        "tool": definition.name,
                        "data": result_payload,
                    }
                ),
                result_type="success",
                tool_telemetry={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "correlation_id": current_correlation,
                    "outcome": "success",
                    "duration_ms": duration_ms,
                },
            )
        except ValidationError as error:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "Tool invocation rejected due to invalid arguments",
                extra={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                },
            )
            return ToolResult(
                text_result_for_llm=_encode_result(
                    {
                        "ok": False,
                        "tool": definition.name,
                        "error": {
                            "code": "INVALID_ARGUMENTS",
                            "message": "Tool arguments were invalid.",
                            "issues": _validation_issues(error),
                        },
                    }
                ),
                result_type="failure",
                error="INVALID_ARGUMENTS",
                tool_telemetry={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "correlation_id": current_correlation,
                    "outcome": "invalid_arguments",
                    "duration_ms": duration_ms,
                },
            )
        except TimeoutError:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "Tool invocation timed out",
                extra={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                },
            )
            return ToolResult(
                text_result_for_llm=_encode_result(
                    {
                        "ok": False,
                        "tool": definition.name,
                        "error": {
                            "code": "TOOL_TIMEOUT",
                            "message": "Tool invocation exceeded its timeout.",
                        },
                    }
                ),
                result_type="failure",
                error="TOOL_TIMEOUT",
                tool_telemetry={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "correlation_id": current_correlation,
                    "outcome": "timeout",
                    "duration_ms": duration_ms,
                },
            )
        except ExternalDependencyUnavailableError:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "Tool invocation failed due to unavailable external dependency",
                extra={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                },
            )
            return ToolResult(
                text_result_for_llm=_encode_result(
                    {
                        "ok": False,
                        "tool": definition.name,
                        "error": {
                            "code": "EXTERNAL_DEPENDENCY_UNAVAILABLE",
                            "message": "External dependency is currently unavailable.",
                        },
                    }
                ),
                result_type="failure",
                error="EXTERNAL_DEPENDENCY_UNAVAILABLE",
                tool_telemetry={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "correlation_id": current_correlation,
                    "outcome": "external_dependency_unavailable",
                    "duration_ms": duration_ms,
                },
            )
        except Exception as error:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.error(
                "Tool invocation failed",
                extra={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "duration_ms": duration_ms,
                    "error_type": type(error).__name__,
                },
            )
            return ToolResult(
                text_result_for_llm=_encode_result(
                    {
                        "ok": False,
                        "tool": definition.name,
                        "error": {
                            "code": "TOOL_EXECUTION_ERROR",
                            "message": "Tool invocation failed.",
                        },
                    }
                ),
                result_type="failure",
                error="TOOL_EXECUTION_ERROR",
                tool_telemetry={
                    "tool_name": definition.name,
                    "tool_call_id": tool_call_id,
                    "session_id": session_id,
                    "correlation_id": current_correlation,
                    "outcome": "execution_error",
                    "duration_ms": duration_ms,
                },
            )
        finally:
            if generated_correlation:
                correlation_id.set("")

    return Tool(
        name=definition.name,
        description=definition.description,
        parameters=definition.params_model.model_json_schema(),
        handler=wrapped_handler,
        skip_permission=definition.skip_permission,
    )


def build_tools(
    definitions: Sequence[ToolDefinition], default_timeout_seconds: float | None = None
) -> list[Tool]:
    """Build and validate a tool registry from definitions."""

    default_timeout = default_timeout_seconds or settings.tool_timeout
    names = [definition.name for definition in definitions]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        raise RuntimeError(
            "Duplicate tool names are not allowed: " + ", ".join(duplicate_names)
        )
    return [build_tool(definition, default_timeout) for definition in definitions]


_registered_tools: list[Tool] = []
_registered_tool_names: list[str] = []


def load_tools() -> list[Tool]:
    """Build and cache the default runtime tool registry."""

    global _registered_tools, _registered_tool_names
    built = build_tools(_build_base_definitions(), settings.tool_timeout)
    _registered_tools = built
    _registered_tool_names = [tool.name for tool in built]
    logger.info(
        "Code-based tools loaded",
        extra={"tool_names": _registered_tool_names, "tool_count": len(_registered_tool_names)},
    )
    return list(_registered_tools)


def get_registered_tools() -> list[Tool]:
    """Return registered code-based tools, loading defaults when needed."""

    if not _registered_tools:
        return load_tools()
    return list(_registered_tools)


def get_registered_tool_names() -> list[str]:
    """Return the names of loaded code-based tools."""

    if not _registered_tools:
        load_tools()
    return list(_registered_tool_names)
