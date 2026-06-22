"""Multi-agent orchestration engine.

Runs agent team patterns by creating Copilot SDK sessions for each role
and yielding SSE event dicts as agents produce output.

Multi-turn support: an in-memory store of prior run results keyed by thread_id
allows follow-up prompts to build on previous team outputs.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any, cast

from copilot.generated.session_events import (
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from copilot.session import CopilotSession, PermissionHandler

from src.config import settings
from src.logging_utils import setup_logging
from src.patterns import AgentRole, get_pattern
from src.skills import get_disabled_skills, get_skill_directories
from src.state import get_client, get_session_pool
from src.token_optimization import truncate_context

logger = setup_logging(settings.log_level)

# In-memory store: thread_id -> list of prior run summaries
_teams_history: dict[str, list[str]] = {}
_team_thread_id_var: ContextVar[str | None] = ContextVar("team_thread_id", default=None)

_MAX_HISTORY_TURNS = 10


def _get_history_context(thread_id: str | None) -> str:
    """Return accumulated context from prior runs for this thread."""
    if not thread_id:
        return ""
    history = _teams_history.get(thread_id, [])
    if not history:
        return ""
    return "Previous team discussions:\n\n" + "\n\n---\n\n".join(history)


def _append_history(thread_id: str | None, run_summary: str) -> None:
    """Store a run's output for future turns."""
    if not thread_id:
        return
    if thread_id not in _teams_history:
        _teams_history[thread_id] = []
    _teams_history[thread_id].append(run_summary)
    # Keep bounded
    if len(_teams_history[thread_id]) > _MAX_HISTORY_TURNS:
        _teams_history[thread_id] = _teams_history[thread_id][-_MAX_HISTORY_TURNS:]


async def _register_team_session(thread_id: str, session: CopilotSession) -> None:
    await get_session_pool().register_active_session(thread_id, session)


async def _unregister_team_session(thread_id: str, session: CopilotSession) -> None:
    await get_session_pool().unregister_active_session(thread_id, session)


async def _collect_agent(role: AgentRole, prompt: str, context: str) -> tuple[str, str]:
    """Run one agent session and return (role_name, full_response).

    Used for parallel execution (e.g. leadership briefings) where we need
    all results before proceeding.
    """
    client = get_client()
    context_body = truncate_context(context)
    sys_content = role.system_prompt + "\n\nContext:\n" + context_body
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        system_message={"mode": "replace", "content": sys_content},
        streaming=True,
        skill_directories=get_skill_directories(),
        disabled_skills=get_disabled_skills(),
    )
    loop = asyncio.get_running_loop()
    idle_event = asyncio.Event()
    parts: list[str] = []
    error_msg: str | None = None
    thread_id = _team_thread_id_var.get()
    if thread_id is not None:
        await _register_team_session(thread_id, session)

    def on_event(event: SessionEvent) -> None:
        nonlocal error_msg
        match event.data:
            case AssistantMessageDeltaData() as delta:
                parts.append(delta.delta_content)
            case SessionErrorData() as err:
                error_msg = str(err)
                loop.call_soon_threadsafe(idle_event.set)
            case SessionIdleData():
                loop.call_soon_threadsafe(idle_event.set)

    session.on(on_event)
    try:
        await session.send(prompt)
        await asyncio.wait_for(idle_event.wait(), timeout=settings.session_timeout)
    finally:
        if thread_id is not None:
            await _unregister_team_session(thread_id, session)
        await session.disconnect()

    if error_msg:
        raise RuntimeError(f"Agent {role.name} error: {error_msg}")
    return role.name, "".join(parts)


async def _stream_agent(
    role: AgentRole,
    prompt: str,
    context: str,
    round_num: int | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run one agent session and yield AGENT_STARTED/DELTA/END events."""
    client = get_client()
    context_body = truncate_context(context)
    sys_content = role.system_prompt + "\n\nContext:\n" + context_body
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        system_message={"mode": "replace", "content": sys_content},
        streaming=True,
        skill_directories=get_skill_directories(),
        disabled_skills=get_disabled_skills(),
    )
    loop = asyncio.get_running_loop()
    idle_event = asyncio.Event()
    send_queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()
    thread_id = _team_thread_id_var.get()
    if thread_id is not None:
        await _register_team_session(thread_id, session)

    def on_event(event: SessionEvent) -> None:
        match event.data:
            case AssistantMessageDeltaData() as delta:
                loop.call_soon_threadsafe(
                    send_queue.put_nowait,
                    {"type": "delta", "content": delta.delta_content},
                )
            case SessionErrorData() as err:
                loop.call_soon_threadsafe(
                    send_queue.put_nowait,
                    {"type": "error", "content": err.message or "Unknown error"},
                )
                loop.call_soon_threadsafe(idle_event.set)
            case SessionIdleData():
                loop.call_soon_threadsafe(idle_event.set)

    session.on(on_event)
    await session.send(prompt)

    yield {
        "type": "AGENT_STARTED",
        "agent_role": f"{role.emoji} {role.name}",
        "round": round_num,
    }

    full_content: list[str] = []
    try:
        while not idle_event.is_set():
            try:
                msg = await asyncio.wait_for(send_queue.get(), timeout=0.1)
            except TimeoutError:
                continue
            if msg["type"] == "error":
                yield {"type": "TEAMS_ERROR", "message": msg["content"]}
                return
            full_content.append(msg["content"])
            yield {
                "type": "AGENT_MESSAGE_DELTA",
                "agent_role": f"{role.emoji} {role.name}",
                "delta": msg["content"],
            }

        # Drain remaining
        while not send_queue.empty():
            msg = send_queue.get_nowait()
            if msg["type"] == "delta":
                full_content.append(msg["content"])
                yield {
                    "type": "AGENT_MESSAGE_DELTA",
                    "agent_role": f"{role.emoji} {role.name}",
                    "delta": msg["content"],
                }
    finally:
        if thread_id is not None:
            await _unregister_team_session(thread_id, session)
        await session.disconnect()

    yield {
        "type": "AGENT_MESSAGE_END",
        "agent_role": f"{role.emoji} {role.name}",
        "content": "".join(full_content),
        "round": round_num,
    }


def _get_agent_content(events_so_far: list[dict[str, Any]]) -> str:
    """Extract the content from the last AGENT_MESSAGE_END event."""
    for event in reversed(events_so_far):
        if event.get("type") == "AGENT_MESSAGE_END":
            content = cast(str, event.get("content"))
            return content if isinstance(content, str) else ""
    return ""


async def _run_sequential_rounds(
    pattern_roles: list[AgentRole],
    prompt: str,
    max_rounds: int,
    prior_context: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Debate & Critic: sequential rounds until CONVERGED or max_rounds."""
    debate_roles = [r for r in pattern_roles if r.name != "Scribe"]
    scribe = next(r for r in pattern_roles if r.name == "Scribe")
    context_parts: list[str] = [prior_context] if prior_context else []

    for round_num in range(1, max_rounds + 1):
        context = "\n\n".join(context_parts)
        synthesizer_output = ""

        for role in debate_roles:
            events: list[dict[str, Any]] = []
            async for event in _stream_agent(role, prompt, context, round_num):
                events.append(event)
                yield event
            agent_content = _get_agent_content(events)
            context_parts.append(f"[{role.name}] {agent_content}")
            if role.name == "Synthesizer":
                synthesizer_output = agent_content

        if "CONVERGED" in synthesizer_output:
            yield {"type": "ROUND_COMPLETED", "round": round_num, "converged": True}
            break
        yield {"type": "ROUND_COMPLETED", "round": round_num, "converged": False}

    all_context = "\n\n".join(context_parts)
    async for event in _stream_agent(scribe, prompt, all_context):
        yield event


async def _run_feedback_loop(
    pattern_roles: list[AgentRole],
    prompt: str,
    max_rounds: int,
    prior_context: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Generator & Evaluator: feedback loop until PASS or max_rounds."""
    generator = next(r for r in pattern_roles if r.name == "Generator")
    evaluator = next(r for r in pattern_roles if r.name == "Evaluator")
    refiner = next(r for r in pattern_roles if r.name == "Refiner")
    scribe = next(r for r in pattern_roles if r.name == "Scribe")

    current_draft = ""
    evaluator_feedback = ""
    all_context_parts: list[str] = [prior_context] if prior_context else []

    for cycle in range(1, max_rounds + 1):
        if cycle == 1:
            events: list[dict[str, Any]] = []
            async for event in _stream_agent(generator, prompt, "", cycle):
                events.append(event)
                yield event
            current_draft = _get_agent_content(events)
            all_context_parts.append(f"[Generator] {current_draft}")
        else:
            events = []
            ctx = f"Previous draft:\n{current_draft}\n\nFeedback:\n{evaluator_feedback}"
            async for event in _stream_agent(refiner, prompt, ctx, cycle):
                events.append(event)
                yield event
            current_draft = _get_agent_content(events)
            all_context_parts.append(f"[Refiner round {cycle}] {current_draft}")

        events = []
        async for event in _stream_agent(evaluator, prompt, current_draft, cycle):
            events.append(event)
            yield event
        evaluator_feedback = _get_agent_content(events)
        all_context_parts.append(f"[Evaluator round {cycle}] {evaluator_feedback}")

        if "PASS" in evaluator_feedback:
            yield {"type": "ROUND_COMPLETED", "round": cycle, "converged": True}
            break
        yield {"type": "ROUND_COMPLETED", "round": cycle, "converged": False}

    all_context = "\n\n".join(all_context_parts)
    async for event in _stream_agent(scribe, prompt, all_context):
        yield event


async def _run_fan_out_sequential(
    pattern_roles: list[AgentRole],
    prompt: str,
    _max_rounds: int,
    prior_context: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Leadership: CEO agenda → parallel briefings → CEO decision → docs."""
    ceo = next(r for r in pattern_roles if r.name == "CEO")
    briefing_roles = [r for r in pattern_roles if r.name in ("CTO", "CISO", "CFO", "CPO")]
    chief_of_staff = next(r for r in pattern_roles if r.name == "ChiefOfStaff")

    # Phase 1: CEO sets agenda (include prior context)
    agenda_context = "Set the agenda for this discussion."
    if prior_context:
        agenda_context = prior_context + "\n\n" + agenda_context

    # Phase 1: CEO sets agenda
    events: list[dict[str, Any]] = []
    async for event in _stream_agent(ceo, prompt, agenda_context, 1):
        events.append(event)
        yield event
    ceo_agenda = _get_agent_content(events)

    # Phase 2: Parallel briefings (collect all, then yield events)
    tasks = [_collect_agent(role, prompt, ceo_agenda) for role in briefing_roles]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    briefing_parts: list[str] = []
    for result in results:
        if isinstance(result, BaseException):
            yield {"type": "TEAMS_ERROR", "message": str(result)}
            continue
        role_name, content = result
        role = next(r for r in briefing_roles if r.name == role_name)
        yield {
            "type": "AGENT_STARTED",
            "agent_role": f"{role.emoji} {role.name}",
            "round": 2,
        }
        yield {
            "type": "AGENT_MESSAGE_END",
            "agent_role": f"{role.emoji} {role.name}",
            "content": content,
            "round": 2,
        }
        briefing_parts.append(f"[{role_name}] {content}")

    # Phase 3: CEO cross-review and decision
    all_briefings = f"[CEO Agenda] {ceo_agenda}\n\n" + "\n\n".join(briefing_parts)
    events = []
    decision_ctx = all_briefings + "\n\nReview all briefings and make a final decision."
    async for event in _stream_agent(ceo, prompt, decision_ctx, 3):
        events.append(event)
        yield event
    ceo_decision = _get_agent_content(events)

    # Phase 4: Chief of Staff documentation
    full_context = all_briefings + f"\n\n[CEO Decision] {ceo_decision}"
    async for event in _stream_agent(chief_of_staff, prompt, full_context):
        yield event


async def _run_sequential_tasks(
    pattern_roles: list[AgentRole],
    prompt: str,
    max_rounds: int,
    prior_context: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Planner & Executor: plan → execute/validate loop → scribe."""
    planner = next(r for r in pattern_roles if r.name == "Planner")
    executor = next(r for r in pattern_roles if r.name == "Executor")
    validator = next(r for r in pattern_roles if r.name == "Validator")
    scribe = next(r for r in pattern_roles if r.name == "Scribe")

    # Planner creates tasks
    events: list[dict[str, Any]] = []
    planner_ctx = prior_context if prior_context else ""
    async for event in _stream_agent(planner, prompt, planner_ctx, 1):
        events.append(event)
        yield event
    plan = _get_agent_content(events)
    all_context_parts = [f"[Planner] {plan}"]
    if prior_context:
        all_context_parts.insert(0, prior_context)

    # Execute/validate loop
    prior_feedback = ""
    for task_round in range(1, max_rounds + 1):
        ctx = f"Plan:\n{plan}\n\nPrior feedback:\n{prior_feedback}" if prior_feedback else plan
        events = []
        async for event in _stream_agent(executor, prompt, ctx, task_round):
            events.append(event)
            yield event
        executor_output = _get_agent_content(events)
        all_context_parts.append(f"[Executor round {task_round}] {executor_output}")

        events = []
        async for event in _stream_agent(validator, prompt, executor_output, task_round):
            events.append(event)
            yield event
        validator_output = _get_agent_content(events)
        all_context_parts.append(f"[Validator round {task_round}] {validator_output}")

        if "PASS" in validator_output:
            yield {"type": "ROUND_COMPLETED", "round": task_round, "converged": True}
            break
        prior_feedback = validator_output
        yield {"type": "ROUND_COMPLETED", "round": task_round, "converged": False}

    all_context = "\n\n".join(all_context_parts)
    async for event in _stream_agent(scribe, prompt, all_context):
        yield event


async def _run_research_loop(
    pattern_roles: list[AgentRole],
    prompt: str,
    max_rounds: int,
    prior_context: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Research & Report: research/reason loop → reporter."""
    researcher = next(r for r in pattern_roles if r.name == "Researcher")
    reasoner = next(r for r in pattern_roles if r.name == "Reasoner")
    reporter = next(r for r in pattern_roles if r.name == "Reporter")

    prior_feedback = prior_context if prior_context else ""
    research_output = ""

    for round_num in range(1, max_rounds + 1):
        ctx = f"Prior feedback:\n{prior_feedback}" if prior_feedback else ""
        events: list[dict[str, Any]] = []
        async for event in _stream_agent(researcher, prompt, ctx, round_num):
            events.append(event)
            yield event
        research_output = _get_agent_content(events)

        events = []
        async for event in _stream_agent(reasoner, prompt, research_output, round_num):
            events.append(event)
            yield event
        reasoner_output = _get_agent_content(events)

        if "PASS" in reasoner_output:
            yield {"type": "ROUND_COMPLETED", "round": round_num, "converged": True}
            break
        prior_feedback = reasoner_output
        yield {"type": "ROUND_COMPLETED", "round": round_num, "converged": False}

    async for event in _stream_agent(reporter, prompt, research_output):
        yield event


_FLOW_RUNNERS = {
    "sequential_rounds": _run_sequential_rounds,
    "feedback_loop": _run_feedback_loop,
    "fan_out_sequential": _run_fan_out_sequential,
    "sequential_tasks": _run_sequential_tasks,
    "research_loop": _run_research_loop,
}


async def run_teams(
    pattern_id: str,
    prompt: str,
    max_rounds: int = 3,
    thread_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Execute a multi-agent pattern and yield SSE event dicts.

    When *thread_id* is provided, prior run results are included as context
    and the current run's output is appended for future turns.
    """
    pattern = get_pattern(pattern_id)
    if pattern is None:
        yield {"type": "TEAMS_ERROR", "message": f"Unknown pattern: {pattern_id}"}
        return

    run_id = uuid.uuid4().hex[:12]
    yield {"type": "TEAMS_STARTED", "pattern_id": pattern_id, "run_id": run_id}

    runner = _FLOW_RUNNERS.get(pattern.flow_type)
    if runner is None:
        yield {"type": "TEAMS_ERROR", "message": f"Unknown flow type: {pattern.flow_type}"}
        return

    prior_context = _get_history_context(thread_id)
    run_outputs: list[str] = []

    token = _team_thread_id_var.set(thread_id)
    try:
        try:
            async for event in runner(pattern.roles, prompt, max_rounds, prior_context):
                yield event
                # Collect final agent outputs for history
                if event.get("type") == "AGENT_MESSAGE_END":
                    role = event.get("agent_role", "Agent")
                    content = event.get("content", "")
                    run_outputs.append(f"[{role}] {content}")
        except Exception:
            logger.exception("Teams execution error for pattern %s", pattern_id)
            yield {
                "type": "TEAMS_ERROR",
                "message": "An internal error occurred while executing the team workflow.",
            }
            return
    finally:
        _team_thread_id_var.reset(token)

    # Store this run's output for multi-turn context
    if run_outputs:
        summary = f"User prompt: {prompt}\n\n" + "\n\n".join(run_outputs)
        _append_history(thread_id, summary)

    yield {"type": "TEAMS_FINISHED", "pattern_id": pattern_id, "run_id": run_id}
