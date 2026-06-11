"""Fleet-style parallel analysis helpers for general chat."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from copilot.generated.session_events import (
    AssistantMessageData,
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from copilot.session import PermissionHandler

from src.config import settings
from src.logging_utils import setup_logging
from src.skills import get_disabled_skills, get_skill_directories
from src.state import get_client

logger = setup_logging(settings.log_level)

_FLEET_BRANCHES: tuple[tuple[str, str], ...] = (
    (
        "planner",
        "Identify the user's intent, success criteria, and the shortest correct response plan.",
    ),
    (
        "reviewer",
        "Check the request for missing context, risks, edge cases, and likely mistakes.",
    ),
    (
        "drafter",
        "Draft a direct, useful answer or implementation approach for the user.",
    ),
)

_FLEET_SYSTEM_MESSAGE = (
    "You are one branch in a parallel GitHub Copilot fleet for a general chat request. "
    "Work independently and return concise findings for the final answering agent. "
    "Do not address the user directly unless the branch instruction asks for a draft."
)


@dataclass(frozen=True)
class ChatFleetResult:
    """Single branch result from the general-chat fleet."""

    name: str
    content: str


def build_conversation_context(messages: list[dict[str, str]]) -> str:
    """Return compact text context from the AG-UI message history."""
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "message").strip() or "message"
        content = message.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def build_augmented_chat_prompt(prompt: str, fleet_results: list[ChatFleetResult]) -> str:
    """Combine the original user prompt with parallel fleet findings."""
    if not fleet_results:
        return prompt

    formatted_results = "\n\n".join(
        f"[{result.name}]\n{result.content}" for result in fleet_results
    )
    return (
        "Use the following parallel fleet analyses as private context, then answer the "
        "user's original request directly. Do not mention the fleet unless it is relevant "
        "to the answer.\n\n"
        f"{formatted_results}\n\n"
        "Original user request:\n"
        f"{prompt}"
    )


async def run_chat_fleet(prompt: str, conversation_context: str) -> list[ChatFleetResult]:
    """Run bounded parallel Copilot sessions that inform the final chat response."""
    if not prompt.strip():
        return []

    tasks = [
        _run_fleet_branch(name, instruction, prompt, conversation_context)
        for name, instruction in _FLEET_BRANCHES
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[ChatFleetResult] = []
    failures: list[str] = []
    for raw_result in raw_results:
        if isinstance(raw_result, BaseException):
            failures.append(str(raw_result))
        else:
            results.append(raw_result)

    if failures:
        logger.warning(
            "One or more chat fleet branches failed",
            extra={"failure_count": len(failures), "successful_count": len(results)},
        )

    if not results:
        raise RuntimeError("All chat fleet branches failed")

    return results


async def _run_fleet_branch(
    name: str,
    instruction: str,
    prompt: str,
    conversation_context: str,
) -> ChatFleetResult:
    client = get_client()
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        system_message={"mode": "replace", "content": _FLEET_SYSTEM_MESSAGE},
        streaming=True,
        skill_directories=get_skill_directories(),
        disabled_skills=get_disabled_skills(),
    )
    loop = asyncio.get_running_loop()
    idle_event = asyncio.Event()
    result_parts: list[str] = []
    error_message: str | None = None

    def on_event(event: SessionEvent) -> None:
        nonlocal error_message
        match event.data:
            case AssistantMessageDeltaData() as delta:
                result_parts.append(delta.delta_content)
            case AssistantMessageData() as data:
                result_parts.append(data.content)
            case SessionErrorData() as err:
                error_message = err.message
                loop.call_soon_threadsafe(idle_event.set)
            case SessionIdleData():
                loop.call_soon_threadsafe(idle_event.set)

    unsubscribe = session.on(on_event)
    try:
        await session.send(_build_branch_prompt(name, instruction, prompt, conversation_context))
        await asyncio.wait_for(idle_event.wait(), timeout=settings.session_timeout)
    finally:
        unsubscribe()
        await session.disconnect()

    if error_message:
        raise RuntimeError(f"chat fleet branch '{name}' failed: {error_message}")

    return ChatFleetResult(name=name, content="".join(result_parts).strip())


def _build_branch_prompt(
    name: str,
    instruction: str,
    prompt: str,
    conversation_context: str,
) -> str:
    context_section = conversation_context or "(No prior conversation context.)"
    return (
        f"Branch: {name}\n"
        f"Branch instruction: {instruction}\n\n"
        "Conversation context:\n"
        f"{context_section}\n\n"
        "Latest user request:\n"
        f"{prompt}\n\n"
        "Return concise findings only."
    )
