"""Async background job manager for Fleet and Infinite Session features."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from copilot.generated.session_events import (
    AssistantMessageData,
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from copilot.session import PermissionHandler

from src.config import settings
from src.models import JobStatusResponse
from src.skills import get_disabled_skills, get_skill_directories
from src.state import get_client

_jobs: dict[str, JobStatusResponse] = {}


def create_job() -> str:
    """Create a new job entry with status 'pending', return job_id."""
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = JobStatusResponse(
        job_id=job_id, status="pending", created_at=datetime.now(UTC).isoformat()
    )
    return job_id


def get_job(job_id: str) -> JobStatusResponse | None:
    """Return job status or None if not found."""
    return _jobs.get(job_id)


async def _call_session(prompt: str, system_message: str | None) -> str:
    """Run a single Copilot session call and return the response text."""
    client = get_client()
    sys_content = system_message or "You are a helpful assistant."
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        system_message={"mode": "replace", "content": sys_content},
        streaming=True,
        available_tools=[],
        skill_directories=get_skill_directories(),
        disabled_skills=get_disabled_skills(),
    )
    loop = asyncio.get_running_loop()
    idle_event = asyncio.Event()
    result_parts: list[str] = []
    error_msg: str | None = None

    def on_event(event: SessionEvent) -> None:
        nonlocal error_msg
        match event.data:
            case AssistantMessageDeltaData() as delta:
                result_parts.append(delta.delta_content)
            case AssistantMessageData() as data:
                result_parts.append(data.content)
            case SessionErrorData() as err:
                error_msg = str(err)
                loop.call_soon_threadsafe(idle_event.set)
            case SessionIdleData():
                loop.call_soon_threadsafe(idle_event.set)

    session.on(on_event)
    await session.send(prompt)
    await asyncio.wait_for(idle_event.wait(), timeout=settings.session_timeout)
    await session.disconnect()

    if error_msg:
        raise RuntimeError(error_msg)
    return "".join(result_parts)


async def run_fleet(job_id: str, items: list[tuple[str, str | None]]) -> None:
    """Run multiple session calls in parallel (max 20) and collect results."""
    job = _jobs[job_id]
    job.status = "running"

    try:
        semaphore = asyncio.Semaphore(20)

        async def _process(prompt: str, system_message: str | None) -> str:
            async with semaphore:
                return await _call_session(prompt, system_message)

        tasks = [_process(prompt, sys_msg) for prompt, sys_msg in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        job.results = []
        for r in results:
            if isinstance(r, BaseException):
                job.results.append(f"ERROR: {r}")
            else:
                job.results.append(r)

        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)


async def run_infinite_session(
    job_id: str,
    prompt: str,
    iterations: int,
    system_message: str | None,
) -> None:
    """Run chained session calls where output N becomes prompt N+1."""
    job = _jobs[job_id]
    job.status = "running"

    try:
        current_prompt = prompt
        for _ in range(iterations):
            current_prompt = await _call_session(current_prompt, system_message)

        job.result = current_prompt
        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
