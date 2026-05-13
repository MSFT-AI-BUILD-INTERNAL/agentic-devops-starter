"""API route handlers for the AG-UI server."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from copilot.generated.session_events import (
    AssistantMessageData,
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from copilot.session import PermissionHandler
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.config import settings
from src.jobs import create_job, get_job, run_fleet, run_infinite_session
from src.logging_utils import setup_logging
from src.models import (
    FleetRequest,
    InfiniteSessionRequest,
    JobStatusResponse,
    PatternInfo,
    TeamsRequest,
)
from src.orchestrator import run_teams
from src.patterns import PATTERNS
from src.state import get_client

logger = setup_logging(settings.log_level)

router = APIRouter()

# System message for the Copilot session.
_SYSTEM_MESSAGE = (
    "You are a helpful AI assistant powered by GitHub Copilot. "
    "Provide clear, accurate, and well-structured responses."
)


def _build_prompt(messages: list[dict[str, str]]) -> str:
    """Extract the last user message content as the prompt."""
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        return user_messages[-1].get("content", "")
    if messages:
        return messages[-1].get("content", "")
    return ""


def _build_system_message(messages: list[dict[str, str]]) -> str:
    """Build system message with conversation context from prior turns."""
    if len(messages) <= 1:
        return _SYSTEM_MESSAGE

    prior = messages[:-1]
    parts = [f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in prior]
    return _SYSTEM_MESSAGE + "\n\nPrevious conversation:\n" + "\n".join(parts)


def _sse(event: dict[str, Any]) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(event)}\n\n"


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.post("/")
async def agent_endpoint(request: Request) -> StreamingResponse:
    """Handle AG-UI agent requests with Copilot SDK streaming."""
    input_data = await request.json()
    thread_id: str = input_data.get("thread_id") or uuid.uuid4().hex[:12]
    run_id: str = input_data.get("run_id") or uuid.uuid4().hex[:12]
    messages: list[dict[str, str]] = input_data.get("messages", [])

    prompt = _build_prompt(messages)
    system_content = _build_system_message(messages)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            client = get_client()
        except RuntimeError:
            yield _sse({"type": "RUN_ERROR", "message": "CopilotClient not initialized"})
            yield _sse({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})
            return

        # RUN_STARTED
        yield _sse({"type": "RUN_STARTED", "thread_id": thread_id, "run_id": run_id})

        message_id = uuid.uuid4().hex[:12]
        message_started = False
        loop = asyncio.get_running_loop()
        idle_event = asyncio.Event()
        send_queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()

        def on_event(event: SessionEvent) -> None:
            match event.data:
                case AssistantMessageDeltaData() as delta:
                    loop.call_soon_threadsafe(
                        send_queue.put_nowait,
                        {"type": "delta", "content": delta.delta_content},
                    )
                case AssistantMessageData():
                    # The complete message is already delivered via deltas when
                    # streaming=True. Emitting it again would duplicate content.
                    pass
                case SessionErrorData() as err:
                    loop.call_soon_threadsafe(
                        send_queue.put_nowait,
                        {"type": "error", "content": err.message or "Unknown error"},
                    )
                    loop.call_soon_threadsafe(idle_event.set)
                case SessionIdleData():
                    loop.call_soon_threadsafe(idle_event.set)

        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            system_message={"mode": "replace", "content": system_content},
            streaming=True,
            available_tools=[],
        )

        try:
            session.on(on_event)
            await session.send(prompt)

            while not idle_event.is_set():
                try:
                    msg = await asyncio.wait_for(send_queue.get(), timeout=0.1)
                except TimeoutError:
                    continue

                if msg["type"] == "error":
                    yield _sse({"type": "RUN_ERROR", "message": msg["content"]})
                elif msg["type"] == "delta":
                    if not message_started:
                        yield _sse({"type": "TEXT_MESSAGE_START", "message_id": message_id})
                        message_started = True
                    yield _sse({"type": "TEXT_MESSAGE_CONTENT", "delta": msg["content"]})

            # Drain remaining queued events
            while not send_queue.empty():
                msg = send_queue.get_nowait()
                if msg["type"] == "delta":
                    if not message_started:
                        yield _sse({"type": "TEXT_MESSAGE_START", "message_id": message_id})
                        message_started = True
                    yield _sse({"type": "TEXT_MESSAGE_CONTENT", "delta": msg["content"]})

            if message_started:
                yield _sse({"type": "TEXT_MESSAGE_END", "message_id": message_id})

        except Exception:
            logger.exception("Copilot session error; terminating stream")
            yield _sse({"type": "RUN_ERROR", "message": "An internal error occurred"})
        finally:
            await session.destroy()

        # Always emit RUN_FINISHED
        yield _sse({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v1/fleet", status_code=202)
async def fleet_endpoint(request: FleetRequest) -> dict[str, str]:
    job_id = create_job()
    items = [(item.prompt, item.system_message) for item in request.items]
    asyncio.create_task(run_fleet(job_id, items))
    return {"job_id": job_id}


@router.post("/v1/infinite-session", status_code=202)
async def infinite_session_endpoint(request: InfiniteSessionRequest) -> dict[str, str]:
    job_id = create_job()
    asyncio.create_task(
        run_infinite_session(job_id, request.prompt, request.iterations, request.system_message)
    )
    return {"job_id": job_id}


@router.get("/v1/patterns")
async def list_patterns() -> list[PatternInfo]:
    """List available agent team patterns."""
    return [
        PatternInfo(
            id=p.id,
            name=p.name,
            description=p.description,
            roles=[r.name for r in p.roles],
        )
        for p in PATTERNS.values()
    ]


@router.post("/v1/teams/stream")
async def teams_stream(request: TeamsRequest) -> StreamingResponse:
    """Execute a multi-agent pattern with SSE streaming."""
    if request.pattern_id not in PATTERNS:
        raise HTTPException(status_code=404, detail="Pattern not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in run_teams(
            request.pattern_id, request.prompt, request.max_rounds
        ):
            yield _sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/v1/jobs/{job_id}")
async def job_status_endpoint(job_id: str) -> JobStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
