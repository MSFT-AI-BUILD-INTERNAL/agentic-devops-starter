"""API route handlers for the AG-UI server."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from copilot.generated.session_events import (
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

import src.sse_utils as sse_utils
from src.blob_storage import BlobStorageConfigurationError, get_blob_service
from src.config import settings
from src.error_handler import log_and_respond
from src.file_validation import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
    generate_blob_name,
    resolve_content_type,
    validate_file_size,
    validate_file_type,
)
from src.jobs import create_job, get_job, run_fleet, run_infinite_session
from src.logging_utils import setup_logging
from src.models import (
    FleetRequest,
    InfiniteSessionRequest,
    JobStatusResponse,
    PatternInfo,
    TeamsRequest,
    UploadResult,
)
from src.orchestrator import run_teams
from src.patterns import PATTERNS
from src.sse_utils import build_prompt, sse_format
from src.state import FoundrySessionPool, SessionPool, get_foundry_session_pool, get_session_pool

logger = setup_logging(settings.log_level)
sse_utils.set_logger(logger)

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
    input_data = await request.json()
    thread_id: str = input_data.get("thread_id") or uuid.uuid4().hex[:12]
    run_id: str = input_data.get("run_id") or uuid.uuid4().hex[:12]
    messages: list[dict[str, str]] = input_data.get("messages", [])
    attachments: list[dict[str, Any]] | None = input_data.get("attachments")

    prompt = build_prompt(messages, attachments)

    return _chat_streaming_response(
        get_session_pool(),
        thread_id,
        run_id,
        prompt,
        "CopilotClient not initialized",
    )


@router.post("/v1/byok/foundry")
async def foundry_byok_endpoint(request: Request) -> StreamingResponse:
    """Handle AG-UI agent requests with an isolated Azure AI Foundry BYOK session."""
    input_data = await request.json()
    thread_id: str = input_data.get("thread_id") or uuid.uuid4().hex[:12]
    run_id: str = input_data.get("run_id") or uuid.uuid4().hex[:12]
    messages: list[dict[str, str]] = input_data.get("messages", [])
    attachments: list[dict[str, Any]] | None = input_data.get("attachments")

    prompt = build_prompt(messages, attachments)

    return _chat_streaming_response(
        get_foundry_session_pool(),
        thread_id,
        run_id,
        prompt,
        "Foundry BYOK session pool not initialized",
    )


def _chat_streaming_response(
    pool: SessionPool | FoundrySessionPool,
    thread_id: str,
    run_id: str,
    prompt: str,
    initialization_error_message: str,
) -> StreamingResponse:
    """Create a streaming AG-UI response for a dedicated session pool."""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            session = await pool.get_or_create(thread_id)
        except RuntimeError as error:
            logger.exception("Chat session initialization failed", extra={"thread_id": thread_id})
            message = str(error) if "Foundry BYOK is not configured" in str(error) else initialization_error_message
            yield sse_format({"type": "RUN_ERROR", "message": message})
            yield sse_format({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})
            return

        # RUN_STARTED
        yield sse_format({"type": "RUN_STARTED", "thread_id": thread_id, "run_id": run_id})

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
                    yield sse_format({"type": "RUN_ERROR", "message": msg["content"]})
                elif msg["type"] == "delta":
                    if not message_started:
                        yield sse_format({"type": "TEXT_MESSAGE_START", "message_id": message_id})
                        message_started = True
                    yield sse_format({"type": "TEXT_MESSAGE_CONTENT", "delta": msg["content"]})

            # Drain remaining queued events
            while not send_queue.empty():
                msg = send_queue.get_nowait()
                if msg["type"] == "delta":
                    if not message_started:
                        yield sse_format({"type": "TEXT_MESSAGE_START", "message_id": message_id})
                        message_started = True
                    yield sse_format({"type": "TEXT_MESSAGE_CONTENT", "delta": msg["content"]})

            if message_started:
                yield sse_format({"type": "TEXT_MESSAGE_END", "message_id": message_id})

        except Exception:
            logger.exception("Copilot session error; terminating stream")
            yield sse_format({"type": "RUN_ERROR", "message": "An internal error occurred"})
            # On error, disconnect so next request gets a fresh session
            await pool.disconnect(thread_id)
        finally:
            if unsubscribe:
                unsubscribe()

        # Always emit RUN_FINISHED
        yield sse_format({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v1/files/upload")
async def upload_file(file: UploadFile) -> JSONResponse:
    """Upload a file to Azure Blob Storage."""
    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_file_type(content_type, filename)
    except ValueError:
        return log_and_respond(
            logger,
            415,
            "INVALID_TYPE",
            "File type is not allowed.",
            "Rejected file upload due to invalid content type",
            extra={"upload_filename": filename, "content_type": content_type},
            extra_fields={"allowed_types": sorted(ALLOWED_CONTENT_TYPES)},
        )

    content_type = resolve_content_type(content_type, filename)
    content = await file.read()

    try:
        validate_file_size(len(content))
    except ValueError:
        status = 422 if len(content) == 0 else 413
        error_code = "EMPTY_FILE" if len(content) == 0 else "FILE_TOO_LARGE"
        detail = "File is empty." if len(content) == 0 else "File exceeds the maximum allowed size."
        return log_and_respond(
            logger,
            status,
            error_code,
            detail,
            "Rejected file upload due to invalid file size",
            extra={"upload_filename": filename, "size_bytes": len(content)},
            extra_fields={"max_size_bytes": MAX_FILE_SIZE_BYTES},
        )

    blob_name = generate_blob_name(filename)
    try:
        blob_service = get_blob_service()
        blob_service.upload(content, blob_name, content_type)
    except BlobStorageConfigurationError as exc:
        return log_and_respond(
            logger,
            503,
            "STORAGE_NOT_CONFIGURED",
            "Blob storage is not configured on this server. "
            "Set COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT to a valid "
            "https://<account>.blob.core.windows.net URL.",
            "Blob upload failed: storage is not configured",
            extra={"upload_filename": filename},
            exception=exc,
        )
    except Exception:
        return log_and_respond(
            logger,
            502,
            "UPLOAD_FAILED",
            "Failed to upload file to storage",
            "Blob upload failed",
            extra={"upload_filename": filename},
            exception=Exception(),
        )

    result = UploadResult(
        blob_name=blob_name,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
    )
    return JSONResponse(status_code=200, content=result.model_dump())


@router.delete("/v1/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict[str, str]:
    """Disconnect and clean up a conversation thread."""
    pool = get_session_pool()
    await pool.disconnect(thread_id)
    foundry_pool = get_foundry_session_pool()
    await foundry_pool.disconnect(thread_id)
    return {"status": "deleted", "thread_id": thread_id}


@router.post("/v1/threads/{thread_id}/abort")
async def abort_thread(thread_id: str) -> dict[str, str]:
    """Abort the active request for a conversation thread.

    Returns status "aborted" for an active session and "not_found" when the
    thread has no active in-memory session to abort.
    """
    pool = get_session_pool()
    aborted = await pool.abort(thread_id)
    return {"status": "aborted" if aborted else "not_found", "thread_id": thread_id}


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


@router.get("/v1/jobs/{job_id}")
async def job_status_endpoint(job_id: str) -> JobStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
