"""Use cases for multi-agent team patterns."""

from collections.abc import AsyncGenerator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import src.sse_utils as sse_utils
from src.models import PatternInfo, TeamsRequest
from src.orchestrator import run_teams
from src.patterns import PATTERNS
from src.sse_utils import sse_format


async def list_team_patterns() -> list[PatternInfo]:
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


async def stream_team_execution(request: TeamsRequest) -> StreamingResponse:
    """Execute a multi-agent pattern with SSE streaming."""
    if request.pattern_id not in PATTERNS:
        raise HTTPException(status_code=404, detail="Pattern not found")

    prompt = request.prompt
    if request.attachments:
        file_context = sse_utils.resolve_attachments(
            [att.model_dump() for att in request.attachments]
        )
        if file_context:
            prompt = file_context + "\n\n" + prompt

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in run_teams(
            request.pattern_id, prompt, request.max_rounds, request.thread_id
        ):
            yield sse_format(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
