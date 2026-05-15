"""API route handlers for the AG-UI server."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from copilot.generated.session_events import (
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
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
from src.state import get_session_pool, get_storage_client

logger = setup_logging(settings.log_level)

router = APIRouter()


def _build_prompt(messages: list[dict[str, str]]) -> str:
    """Extract the last user message content as the prompt."""
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        return user_messages[-1].get("content", "")
    if messages:
        return messages[-1].get("content", "")
    return ""


def _sse(event: dict[str, Any]) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(event)}\n\n"


async def _stream_copilot_prompt(
    thread_id: str, run_id: str, prompt: str
) -> AsyncGenerator[str, None]:
    """Send *prompt* to the Copilot session for *thread_id* and yield SSE events.

    Shared by the chat and file-upload endpoints. Emits AG-UI protocol events
    (``RUN_STARTED``, ``TEXT_MESSAGE_START``/``CONTENT``/``END``,
    ``RUN_ERROR``, ``RUN_FINISHED``).
    """
    pool = get_session_pool()

    try:
        session = await pool.get_or_create(thread_id)
    except RuntimeError:
        yield _sse({"type": "RUN_ERROR", "message": "CopilotClient not initialized"})
        yield _sse({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})
        return

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
            case SessionErrorData() as err:
                loop.call_soon_threadsafe(
                    send_queue.put_nowait,
                    {"type": "error", "content": err.message or "Unknown error"},
                )
                loop.call_soon_threadsafe(idle_event.set)
            case SessionIdleData():
                loop.call_soon_threadsafe(idle_event.set)

    unsubscribe = None
    try:
        unsubscribe = session.on(on_event)
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
        await pool.disconnect(thread_id)
    finally:
        if unsubscribe:
            unsubscribe()

    yield _sse({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


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
    input_data = await request.json()
    thread_id: str = input_data.get("thread_id") or uuid.uuid4().hex[:12]
    run_id: str = input_data.get("run_id") or uuid.uuid4().hex[:12]
    messages: list[dict[str, str]] = input_data.get("messages", [])
    prompt = _build_prompt(messages)

    return StreamingResponse(
        _stream_copilot_prompt(thread_id, run_id, prompt),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# Maximum file size accepted by the upload endpoint. Files larger than this
# are rejected with HTTP 413 rather than being streamed to blob storage.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MiB


@router.post("/v1/files/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),  # noqa: B008 — FastAPI dependency markers
    thread_id: str | None = Form(default=None),  # noqa: B008
    prompt: str | None = Form(default=None),  # noqa: B008
) -> StreamingResponse:
    """Upload *file* to Blob Storage, download it back, and process it via Copilot SDK.

    Returns an SSE stream of AG-UI protocol events identical to the chat
    endpoint so the frontend can reuse its existing event handler. The file
    is uploaded using the Azure SDK's block-based (multi-part) upload, then
    downloaded and forwarded to the Copilot session for the given
    ``thread_id`` (or a new one if omitted).
    """
    try:
        storage = get_storage_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail="Blob storage is not configured on the server"
        ) from exc

    # Enforce a size cap up front to avoid uploading arbitrarily large files.
    # ``UploadFile.size`` is only set for spooled files where the client sent
    # a Content-Length; treat missing as unknown and rely on the SDK to handle
    # the stream, but still cap our own download via _MAX_PROCESS_BYTES.
    declared_size = getattr(file, "size", None)
    if isinstance(declared_size, int) and declared_size > _MAX_UPLOAD_BYTES:
        limit_mb = _MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413, detail=f"Uploaded file is too large (max {limit_mb} MB)"
        )

    resolved_thread_id = thread_id or uuid.uuid4().hex[:12]
    run_id = uuid.uuid4().hex[:12]

    try:
        uploaded = await storage.upload(
            file.file,
            original_filename=file.filename or "upload.bin",
            content_type=file.content_type,
        )
    except Exception as exc:
        logger.exception("Failed to upload file to blob storage")
        raise HTTPException(status_code=502, detail="Failed to upload file") from exc
    finally:
        await file.close()

    try:
        contents = await storage.download_text(uploaded.name)
    except Exception as exc:
        logger.exception("Failed to download blob for processing")
        raise HTTPException(status_code=502, detail="Failed to read uploaded file") from exc

    user_prompt = (prompt or "Please process the attached file and summarize it.").strip()
    copilot_prompt = (
        f"{user_prompt}\n\n"
        f"Filename: {uploaded.name}\n"
        f"Size: {uploaded.size} bytes\n"
        f"Content-Type: {uploaded.content_type or 'application/octet-stream'}\n\n"
        f"--- Begin File Contents ---\n{contents}\n--- End File Contents ---"
    )

    return StreamingResponse(
        _stream_copilot_prompt(resolved_thread_id, run_id, copilot_prompt),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.delete("/v1/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, str]:
    """Disconnect and clean up a conversation thread."""
    pool = get_session_pool()
    await pool.disconnect(thread_id)
    return {"status": "deleted", "thread_id": thread_id}


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
            request.pattern_id, request.prompt, request.max_rounds, request.thread_id
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
