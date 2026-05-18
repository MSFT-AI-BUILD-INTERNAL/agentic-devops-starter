"""API route handlers for the AG-UI server."""

import asyncio
import base64
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
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from src.blob_storage import get_blob_service
from src.config import settings
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
from src.state import get_session_pool

logger = setup_logging(settings.log_level)

router = APIRouter()


def _build_prompt(
    messages: list[dict[str, str]], attachments: list[dict[str, Any]] | None = None
) -> str:
    """Extract the last user message content as the prompt, prepending file context if present."""
    user_messages = [m for m in messages if m.get("role") == "user"]
    if user_messages:
        content = user_messages[-1].get("content", "")
    elif messages:
        content = messages[-1].get("content", "")
    else:
        content = ""

    if attachments:
        try:
            file_context = _resolve_attachments(attachments)
        except Exception:
            file_context = ""
        if file_context:
            content = file_context + "\n\n" + content

    return content


def _resolve_attachments(attachments: list[dict[str, Any]]) -> str:
    """Download attached blobs and format as context for the AI prompt."""
    parts: list[str] = []
    blob_service = get_blob_service()

    for att in attachments:
        blob_name = att.get("blob_name", "")
        original_filename = att.get("original_filename", "file")
        content_type = att.get("content_type", "")

        try:
            # Use synchronous download (azure SDK sync client)
            container_client = blob_service._client.get_container_client(
                blob_service._container_name
            )
            blob_client = container_client.get_blob_client(blob_name)
            downloader = blob_client.download_blob()
            content: bytes = downloader.readall()

            if content_type.startswith("text/") or content_type == "application/json":
                text = content.decode("utf-8", errors="replace")
                parts.append(f"[File: {original_filename}]\n{text}")
            elif content_type == "application/pdf":
                encoded = base64.b64encode(content).decode("ascii")
                parts.append(
                    f"[File: {original_filename} (PDF, {len(content)} bytes, base64-encoded)]\n"
                    f"{encoded}"
                )
            else:
                encoded = base64.b64encode(content).decode("ascii")
                parts.append(
                    f"[File: {original_filename} ({content_type}, {len(content)} bytes, "
                    f"base64-encoded)]\n{encoded}"
                )
        except Exception:
            logger.exception("Failed to download attachment", extra={"blob_name": blob_name})
            parts.append(f"[File: {original_filename} — failed to load]")

    return "\n\n".join(parts)


def _sse(event: dict[str, Any]) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(event)}\n\n"


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

    prompt = _build_prompt(messages, attachments)

    async def event_generator() -> AsyncGenerator[str, None]:
        pool = get_session_pool()

        try:
            session = await pool.get_or_create(thread_id)
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
            # On error, disconnect so next request gets a fresh session
            await pool.disconnect(thread_id)
        finally:
            if unsubscribe:
                unsubscribe()

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


@router.post("/v1/files/upload")
async def upload_file(file: UploadFile) -> JSONResponse:
    """Upload a file to Azure Blob Storage."""
    filename = file.filename or "unnamed"

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    try:
        validate_file_type(content_type, filename)
    except ValueError:
        logger.warning(
            "Rejected file upload due to invalid content type",
            extra={"upload_filename": filename, "content_type": content_type},
        )
        return JSONResponse(
            status_code=415,
            content={
                "error": "INVALID_TYPE",
                "detail": "File type is not allowed.",
                "allowed_types": sorted(ALLOWED_CONTENT_TYPES),
            },
        )

    # Some clients/OS send generic types (e.g. application/octet-stream) for
    # known extensions like .md — normalize so blob metadata is accurate.
    content_type = resolve_content_type(content_type, filename)

    # Read file content
    content = await file.read()

    # Validate size
    try:
        validate_file_size(len(content))
    except ValueError:
        status = 422 if len(content) == 0 else 413
        logger.warning(
            "Rejected file upload due to invalid file size",
            extra={"upload_filename": filename, "size_bytes": len(content), "status": status},
        )
        return JSONResponse(
            status_code=status,
            content={
                "error": "EMPTY_FILE" if len(content) == 0 else "FILE_TOO_LARGE",
                "detail": "File is empty." if len(content) == 0 else "File exceeds the maximum allowed size.",
                "max_size_bytes": MAX_FILE_SIZE_BYTES,
            },
        )

    # Generate blob name and upload
    blob_name = generate_blob_name(filename)
    try:
        blob_service = get_blob_service()
        await blob_service.upload(content, blob_name, content_type)
    except Exception:
        logger.exception("Blob upload failed", extra={"upload_filename": filename})
        return JSONResponse(
            status_code=502,
            content={"error": "UPLOAD_FAILED", "detail": "Failed to upload file to storage"},
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

    prompt = request.prompt
    if request.attachments:
        file_context = _resolve_attachments(
            [att.model_dump() for att in request.attachments]
        )
        if file_context:
            prompt = file_context + "\n\n" + prompt

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in run_teams(
            request.pattern_id, prompt, request.max_rounds, request.thread_id
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
