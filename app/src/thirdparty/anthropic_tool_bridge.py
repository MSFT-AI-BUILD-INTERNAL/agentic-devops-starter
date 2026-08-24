"""Anthropic tool-use bridge core: pending-call state and SDK tool adapters.

This module bridges native Anthropic ``tools`` / ``tool_use`` / ``tool_result``
content blocks (as used by clients such as Claude Code) onto the Copilot
SDK's own tool-invocation model.

Why a bridge is needed
-----------------------
The Copilot SDK only supports tools registered as :class:`copilot.tools.Tool`
objects at session creation/resume time. When the model decides to call one,
the SDK looks up the registered handler (``CopilotSession._get_tool_handler``)
and awaits it; once the handler returns a :class:`~copilot.tools.ToolResult`,
the SDK -- not the caller -- forwards it to the CLI via the
``tools.handle_pending_tool_call`` RPC
(see ``CopilotSession._execute_tool_and_respond``).

Anthropic-style clients execute tools themselves: the server must instead
emit a ``tool_use`` content block and end the turn, and the client replies
later (in a new request) with a ``tool_result`` block that must resume that
specific call. To reconcile the two models, each Anthropic tool is
registered with the SDK as a :class:`~copilot.tools.Tool` whose handler does
not execute anything itself. Instead it:

1. Registers a pending call in :class:`PendingToolCallRegistry` and awaits a
   future (bounded by a timeout).
2. The SDK also broadcasts the same invocation as an
   ``ExternalToolRequestedData`` session event (visible via ``session.on()``),
   which a route handler can turn into a native Anthropic ``tool_use`` block
   with :func:`tool_use_content_block` and stream/return to the client,
   ending the turn per the Anthropic protocol.
3. On the client's next request, the route extracts ``tool_result`` blocks
   (see :func:`src.thirdparty.anthropic_adapter.extract_tool_result_blocks`)
   and calls :func:`resolve_pending_tool_call` for each one. This resolves
   the future from step 1, so the still-awaiting Tool handler returns and
   the SDK resumes the underlying turn via ``handle_pending_tool_call``.

This module intentionally never touches ``CopilotSession._execute_tool_and_respond``
or ``session.rpc`` directly: registering a Tool and returning a
``ToolResult`` from its handler is the only public/idiomatic way to resume a
pending SDK tool call.

Route integration (not part of this module)
--------------------------------------------
Routes are expected to:

* Build bridge tools with :func:`build_bridge_tools` from
  :func:`src.thirdparty.anthropic_adapter.parse_tool_definitions`, and pass
  them into ``client.create_session``/``resume_session`` (typically merged
  with :func:`src.runtime.tools.get_registered_tools`) whenever a request
  declares Anthropic ``tools``.
* Match ``ExternalToolRequestedData`` in the session event handler and emit
  the corresponding SSE tool_use block from
  :mod:`src.thirdparty.anthropic_stream`.
* Resolve pending calls with :func:`resolve_pending_tool_call` when a
  request's ``tool_result`` blocks arrive.

None of that wiring happens here; this module only provides the safe,
bounded, timeout-aware state and the SDK tool adapters routes can compose.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from copilot.tools import Tool, ToolInvocation, ToolResult

from src.thirdparty.anthropic_models import AnthropicToolDefinition, AnthropicToolResultBlock

# How long a bridged tool call waits for a matching tool_result before it is
# abandoned. Chosen to comfortably cover a human-in-the-loop client-side tool
# execution without holding SDK/model turn state open indefinitely.
DEFAULT_PENDING_TIMEOUT_SECONDS = 300.0

# Bounds preventing unbounded memory growth from abandoned or leaked calls
# (e.g. a client that emits tool_use requests but never replies).
MAX_PENDING_CALLS_PER_KEY = 32
MAX_TOTAL_PENDING_CALLS = 2048


class ToolBridgeCapacityError(RuntimeError):
    """Raised when a pending-call registry would exceed its configured bounds."""


@dataclass
class _PendingCall:
    tool_call_id: str
    tool_name: str
    key: str
    future: asyncio.Future[ToolResult]
    created_at: float = field(default_factory=time.monotonic)


class PendingToolCallRegistry:
    """Tracks in-flight Anthropic tool calls awaiting a client-supplied result.

    Entries are keyed by an opaque isolation/thread ``key`` (see
    :func:`bridge_key`) plus the Anthropic tool call id, so calls from
    different isolation scopes or threads can never collide or be resolved
    by the wrong caller. Registration is bounded both per-key and globally;
    exceeding either bound raises :class:`ToolBridgeCapacityError` instead of
    growing state without limit. All mutation happens under an internal
    lock, so the registry is safe to share across concurrent requests.
    """

    def __init__(
        self,
        *,
        max_calls_per_key: int = MAX_PENDING_CALLS_PER_KEY,
        max_total_calls: int = MAX_TOTAL_PENDING_CALLS,
    ) -> None:
        self._calls: dict[str, _PendingCall] = {}
        self._by_key: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()
        self._max_calls_per_key = max_calls_per_key
        self._max_total_calls = max_total_calls

    @staticmethod
    def _entry_id(key: str, tool_call_id: str) -> str:
        return f"{key}\x00{tool_call_id}"

    async def register(
        self, key: str, tool_call_id: str, tool_name: str
    ) -> asyncio.Future[ToolResult]:
        """Register a new pending call and return the future its handler should await.

        Raises :class:`ToolBridgeCapacityError` if the per-key or global
        bound would be exceeded, or if ``tool_call_id`` is already pending
        for ``key``.
        """
        entry_id = self._entry_id(key, tool_call_id)
        async with self._lock:
            if entry_id in self._calls:
                raise ToolBridgeCapacityError(
                    f"Duplicate pending tool call id '{tool_call_id}' for key '{key}'."
                )
            if len(self._calls) >= self._max_total_calls:
                raise ToolBridgeCapacityError("Global pending tool-call limit reached.")
            existing_for_key = self._by_key.get(key, set())
            if len(existing_for_key) >= self._max_calls_per_key:
                raise ToolBridgeCapacityError(f"Pending tool-call limit reached for key '{key}'.")
            future: asyncio.Future[ToolResult] = asyncio.get_running_loop().create_future()
            self._calls[entry_id] = _PendingCall(
                tool_call_id=tool_call_id, tool_name=tool_name, key=key, future=future
            )
            self._by_key.setdefault(key, set()).add(entry_id)
            return future

    async def release(self, key: str, tool_call_id: str) -> None:
        """Remove bookkeeping for a call whose future has already settled or was abandoned."""
        entry_id = self._entry_id(key, tool_call_id)
        async with self._lock:
            self._calls.pop(entry_id, None)
            keys = self._by_key.get(key)
            if keys is not None:
                keys.discard(entry_id)
                if not keys:
                    self._by_key.pop(key, None)

    async def resolve(self, key: str, tool_call_id: str, result: ToolResult) -> bool:
        """Resolve a pending call with *result*.

        Returns False if no such call is pending (unknown id, already
        settled, or resolved for the wrong isolation/thread key), so callers
        can distinguish a successful resume from a stale/duplicate
        tool_result.
        """
        entry_id = self._entry_id(key, tool_call_id)
        async with self._lock:
            call = self._calls.get(entry_id)
            if call is None or call.future.done():
                return False
            call.future.set_result(result)
            return True

    async def cancel(self, key: str, tool_call_id: str) -> bool:
        """Cancel a single pending call. Returns False if unknown or already settled."""
        entry_id = self._entry_id(key, tool_call_id)
        async with self._lock:
            call = self._calls.pop(entry_id, None)
            if call is not None:
                keys = self._by_key.get(key)
                if keys is not None:
                    keys.discard(entry_id)
                    if not keys:
                        self._by_key.pop(key, None)
            if call is None or call.future.done():
                return False
            call.future.cancel()
            return True

    async def cancel_all(self, key: str) -> int:
        """Cancel every pending call for *key* (e.g. on session disconnect/eviction).

        Returns the number of calls actually cancelled.
        """
        async with self._lock:
            entry_ids = list(self._by_key.get(key, ()))
            cancelled = 0
            for entry_id in entry_ids:
                call = self._calls.pop(entry_id, None)
                if call is not None and not call.future.done():
                    call.future.cancel()
                    cancelled += 1
            self._by_key.pop(key, None)
            return cancelled

    async def pending_count(self, key: str | None = None) -> int:
        """Return the number of pending calls, optionally scoped to *key*."""
        async with self._lock:
            if key is None:
                return len(self._calls)
            return len(self._by_key.get(key, ()))


def bridge_key(isolation_session_id: str, thread_id: str) -> str:
    """Return the :class:`PendingToolCallRegistry` key for an isolation scope and thread.

    Mirrors the session pool's own keying (isolation session id + thread id)
    so pending tool calls are scoped identically to the underlying Copilot
    SDK session they belong to.
    """
    return f"{isolation_session_id}:{thread_id}"


async def _await_bridge_tool_result(
    registry: PendingToolCallRegistry,
    key: str,
    invocation: ToolInvocation,
    timeout_seconds: float,
) -> ToolResult:
    """Register *invocation* as pending and block until it is resolved or times out."""
    tool_call_id = invocation.tool_call_id or ""
    if not tool_call_id:
        return ToolResult(
            text_result_for_llm="Tool invocation is missing a tool_call_id.",
            result_type="failure",
            error="MISSING_TOOL_CALL_ID",
        )
    try:
        future = await registry.register(key, tool_call_id, invocation.tool_name)
    except ToolBridgeCapacityError as exc:
        return ToolResult(
            text_result_for_llm="Tool bridge is at capacity; the call was rejected.",
            result_type="failure",
            error=str(exc),
        )
    try:
        return await asyncio.wait_for(future, timeout=timeout_seconds)
    except TimeoutError:
        return ToolResult(
            text_result_for_llm=(
                "Timed out waiting for the client to return a tool_result for this call."
            ),
            result_type="timeout",
            error="TOOL_RESULT_TIMEOUT",
        )
    except asyncio.CancelledError:
        return ToolResult(
            text_result_for_llm="The pending tool call was cancelled.",
            result_type="rejected",
            error="TOOL_CALL_CANCELLED",
        )
    finally:
        await registry.release(key, tool_call_id)


def build_bridge_tools(
    tool_definitions: list[AnthropicToolDefinition],
    registry: PendingToolCallRegistry,
    key: str,
    *,
    timeout_seconds: float = DEFAULT_PENDING_TIMEOUT_SECONDS,
) -> list[Tool]:
    """Build Copilot SDK :class:`~copilot.tools.Tool` objects for the given Anthropic tools.

    Each returned Tool's handler performs no work itself: it registers a
    pending call in *registry* and blocks (bounded by *timeout_seconds*)
    until :meth:`PendingToolCallRegistry.resolve` is called for its
    ``tool_call_id`` -- normally once the client's next request supplies a
    matching ``tool_result`` content block. Returning a Tool with a handler
    is required because the SDK only invokes ``handle_pending_tool_call``
    from within a registered handler's return path.
    """
    tools: list[Tool] = []
    for definition in tool_definitions:

        async def handler(invocation: ToolInvocation) -> ToolResult:
            return await _await_bridge_tool_result(registry, key, invocation, timeout_seconds)

        tools.append(
            Tool(
                name=definition.name,
                description=definition.description,
                parameters=definition.input_schema or None,
                handler=handler,
            )
        )
    return tools


def _tool_result_content_to_text(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        else:
            parts.append(json.dumps(block, ensure_ascii=False))
    return "\n".join(parts)


def _tool_result_block_to_tool_result(block: AnthropicToolResultBlock) -> ToolResult:
    text = _tool_result_content_to_text(block.content)
    if block.is_error:
        return ToolResult(
            text_result_for_llm=text,
            result_type="failure",
            error=text or "tool_result reported an error",
        )
    return ToolResult(text_result_for_llm=text, result_type="success")


async def resolve_pending_tool_call(
    registry: PendingToolCallRegistry, key: str, block: AnthropicToolResultBlock
) -> bool:
    """Resolve the pending SDK tool call matching *block*'s ``tool_use_id``.

    Returns False if no matching pending call is found for *key* (unknown,
    already resolved, or belongs to a different isolation/thread scope).
    """
    result = _tool_result_block_to_tool_result(block)
    return await registry.resolve(key, block.tool_use_id, result)


def tool_use_content_block(tool_call_id: str, tool_name: str, arguments: Any) -> dict[str, Any]:
    """Return an Anthropic-shaped ``tool_use`` content block for a non-streaming response.

    Mirrors the payload of an ``ExternalToolRequestedData`` session event
    (``tool_call_id``, ``tool_name``, ``arguments``) into the dict shape
    expected in an Anthropic Messages API response's ``content`` list.
    """
    return {
        "type": "tool_use",
        "id": tool_call_id,
        "name": tool_name,
        "input": arguments if isinstance(arguments, dict) else {},
    }
