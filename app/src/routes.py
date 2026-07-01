"""API route wiring for the AG-UI server."""

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from src.models import (
    FleetRequest,
    InfiniteSessionRequest,
    JobStatusResponse,
    PatternInfo,
    TeamsRequest,
)
from src.state import get_foundry_session_pool, get_session_pool
from src.use_cases.background_jobs import (
    get_job_status,
    start_fleet_job,
    start_infinite_session_job,
)
from src.use_cases.chat import stream_chat
from src.use_cases.file_upload import upload_file_to_blob
from src.use_cases.teams import list_team_patterns, stream_team_execution
from src.use_cases.threads import abort_thread_session, delete_thread_sessions

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.post("/")
async def agent_endpoint(request: Request) -> StreamingResponse:
    """Handle AG-UI agent requests with Copilot SDK multi-turn streaming.

    The session pool keeps Copilot sessions alive between turns so the SDK
    manages full conversation history internally. Only the latest user message
    is sent; prior context is maintained by the SDK session.
    """
    return await stream_chat(
        request,
        get_session_pool(),
        "CopilotClient not initialized",
    )


@router.post("/v1/byok/foundry")
async def foundry_byok_endpoint(request: Request) -> StreamingResponse:
    """Handle AG-UI agent requests with an isolated Azure AI Foundry BYOK session."""
    return await stream_chat(
        request,
        get_foundry_session_pool(),
        "Foundry BYOK session pool not initialized",
    )


@router.post("/v1/files/upload")
async def upload_file(file: UploadFile) -> JSONResponse:
    """Upload a file to Azure Blob Storage."""
    return await upload_file_to_blob(file)


@router.delete("/v1/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, str]:
    """Disconnect and clean up a conversation thread."""
    return await delete_thread_sessions(thread_id, get_session_pool(), get_foundry_session_pool())


@router.post("/v1/threads/{thread_id}/abort")
async def abort_thread(thread_id: str) -> dict[str, str]:
    """Abort the active request for a conversation thread.

    Returns status "aborted" for an active session and "not_found" when the
    thread has no active in-memory session to abort.
    """
    return await abort_thread_session(thread_id, get_session_pool())


@router.post("/v1/fleet", status_code=202)
async def fleet_endpoint(request: FleetRequest) -> dict[str, str]:
    return await start_fleet_job(request)


@router.post("/v1/infinite-session", status_code=202)
async def infinite_session_endpoint(request: InfiniteSessionRequest) -> dict[str, str]:
    return await start_infinite_session_job(request)


@router.get("/v1/patterns")
async def list_patterns() -> list[PatternInfo]:
    """List available agent team patterns."""
    return await list_team_patterns()


@router.post("/v1/teams/stream")
async def teams_stream(request: TeamsRequest) -> StreamingResponse:
    """Execute a multi-agent pattern with SSE streaming."""
    return await stream_team_execution(request)


@router.get("/v1/jobs/{job_id}")
async def job_status_endpoint(job_id: str) -> JobStatusResponse:
    return await get_job_status(job_id)
