"""API route handlers for the AG-UI server."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlencode

from copilot.generated.session_events import (
    AssistantMessageDeltaData,
    SessionErrorData,
    SessionEvent,
    SessionIdleData,
)
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse

import src.api.sse_utils as sse_utils
from src.api.auth import (
    SESSION_COOKIE,
    create_oauth_state,
    exchange_code,
    get_user_isolation_namespace,
    get_user_session_id,
    get_user_token,
    oauth_state_context,
    poll_device_token,
    request_device_code,
    set_session_cookie,
    store_token,
    verify_oauth_state,
)
from src.api.error_handler import log_and_respond
from src.api.models import (
    DeviceTokenRequest,
    FleetRequest,
    InfiniteSessionRequest,
    JobStatusResponse,
    MCPToolResponse,
    PatternInfo,
    TeamsRequest,
    UploadResult,
)
from src.api.sse_utils import build_prompt, sse_format
from src.core.config import settings
from src.core.logging_utils import setup_logging
from src.runtime.isolation import normalize_isolation_session_id
from src.runtime.jobs import create_job, get_job, run_fleet, run_infinite_session
from src.runtime.state import (
    AISessionPool,
    FoundryConfigurationError,
    get_foundry_session_pool,
    get_session_pool,
)
from src.storage.blob_storage import BlobStorageConfigurationError, get_blob_service
from src.storage.file_validation import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
    generate_blob_name,
    resolve_content_type,
    validate_file_size,
    validate_file_type,
)
from src.teams.orchestrator import run_teams
from src.teams.patterns import PATTERNS
from src.thirdparty.anthropic_tool_bridge import PendingToolCallRegistry

logger = setup_logging(settings.log_level)
sse_utils.set_logger(logger)

router = APIRouter()


@router.get("/auth/login")
async def github_login(request: Request) -> RedirectResponse:
    """Redirect the browser to GitHub's OAuth authorization page."""
    if (
        not settings.github_client_id
        or not settings.github_client_secret
        or not settings.github_oauth_redirect_uri
    ):
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = create_oauth_state(oauth_state_context(request))
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_oauth_redirect_uri,
            "state": state,
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@router.get("/auth/callback")
async def github_callback(request: Request, code: str, state: str) -> RedirectResponse:
    """Complete GitHub OAuth and establish an opaque browser session."""
    if not verify_oauth_state(state, oauth_state_context(request)):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    session_id = store_token(await exchange_code(code))
    response = RedirectResponse("/")
    set_session_cookie(response, session_id)
    return response


@router.get("/auth/session")
async def github_session(request: Request) -> dict[str, bool]:
    """Confirm that the current browser has an authenticated GitHub session."""
    get_user_token(request)
    return {"authenticated": True}


@router.post("/auth/logout", status_code=204)
async def github_logout() -> Response:
    """End the current browser session and discard its GitHub token."""
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/auth/device")
async def github_device_code() -> JSONResponse:
    """Start a GitHub Device Flow — returns user_code and verification_uri."""
    result = await request_device_code()
    return JSONResponse(
        {
            "user_code": result.user_code,
            "verification_uri": result.verification_uri,
            "device_code": result.device_code,
            "expires_in": result.expires_in,
            "interval": result.interval,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.post("/auth/device/token")
async def github_device_token(body: DeviceTokenRequest) -> JSONResponse:
    """Poll once for a Device Flow token.

    Client should retry when status is ``pending``. When status is ``slow_down``,
    add ``interval`` seconds to the current polling interval for subsequent attempts.
    """
    result = await poll_device_token(body.device_code)
    if result.status == "ok":
        payload: dict[str, object] = {"session_token": result.session_token}
    elif result.status == "slow_down":
        payload = {"status": result.status, "interval": result.interval}
    else:
        payload = {"status": result.status}
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


def _resolve_isolation_session_id(request: Request, fallback: str) -> str:
    raw = request.headers.get(settings.isolation_session_header)
    return normalize_isolation_session_id(raw, fallback)


def _resolve_authenticated_isolation_session_id(request: Request, fallback: str) -> str:
    """Namespace a client-selected isolation ID by the authenticated browser session."""
    client_isolation_id = _resolve_isolation_session_id(request, fallback)
    session_id = get_user_session_id(request)
    return get_user_isolation_namespace(session_id, client_isolation_id)


def _require_thirdparty_github_pat() -> str:
    token = settings.thirdparty_github_pat.strip()
    if not token:
        raise HTTPException(status_code=503, detail="THIRDPARTY_GITHUB_PAT is not configured")
    return token


# Grace window used after the first bridged tool_use request in a turn to
# catch further tool_use requests the Copilot SDK emits for the same turn
# (e.g. parallel tool calls). The SDK has no explicit "all tool calls for
# this turn were issued" signal, so a brief post-first-call quiescence
# window is used as a pragmatic heuristic instead.
_ANTHROPIC_TOOL_USE_GRACE_SECONDS = 0.15

# Content block types the Anthropic bridge still cannot handle even with
# the tool-use bridge enabled; tool_use/tool_result are now handled by it.
_ANTHROPIC_UNSUPPORTED_BLOCK_TYPES = frozenset({"image", "document", "thinking"})

# Process-wide registry of in-flight Anthropic tool calls awaiting a
# client-supplied tool_result, shared across every /v1/messages request for
# the lifetime of the server (see src.thirdparty.anthropic_tool_bridge).
_anthropic_tool_bridge_registry: PendingToolCallRegistry | None = None


def _get_anthropic_tool_bridge_registry() -> PendingToolCallRegistry:
    """Return the process-wide registry, creating it on first use."""
    global _anthropic_tool_bridge_registry
    if _anthropic_tool_bridge_registry is None:
        _anthropic_tool_bridge_registry = PendingToolCallRegistry()
    return _anthropic_tool_bridge_registry



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
    github_token = get_user_token(request)
    isolation_session_id = _resolve_authenticated_isolation_session_id(request, thread_id)
    messages: list[dict[str, str]] = input_data.get("messages", [])
    attachments: list[dict[str, Any]] | None = input_data.get("attachments")

    try:
        prompt = build_prompt(messages, attachments, isolation_session_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    return _chat_streaming_response(
        get_session_pool(),
        isolation_session_id,
        github_token,
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
    isolation_session_id = _resolve_isolation_session_id(request, thread_id)
    messages: list[dict[str, str]] = input_data.get("messages", [])
    attachments: list[dict[str, Any]] | None = input_data.get("attachments")

    try:
        prompt = build_prompt(messages, attachments, isolation_session_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error

    return _chat_streaming_response(
        get_foundry_session_pool(),
        isolation_session_id,
        None,
        thread_id,
        run_id,
        prompt,
        "Foundry BYOK session pool not initialized",
    )


def _chat_streaming_response(
    pool: AISessionPool,
    isolation_session_id: str,
    github_token: str | None,
    thread_id: str,
    run_id: str,
    prompt: str,
    fallback_error_message: str,
) -> StreamingResponse:
    """Create a streaming AG-UI response for a dedicated session pool."""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            session = await pool.get_or_create(
                thread_id, github_token, isolation_session_id=isolation_session_id
            )
        except RuntimeError as error:
            logger.exception("Chat session initialization failed", extra={"thread_id": thread_id})
            message = initialization_error_message(error, fallback_error_message)
            yield sse_format({"type": "RUN_ERROR", "message": message})
            yield sse_format({"type": "RUN_FINISHED", "thread_id": thread_id, "run_id": run_id})
            return

        # RUN_STARTED
        yield sse_format({"type": "RUN_STARTED", "thread_id": thread_id, "run_id": run_id})

        message_id = uuid.uuid4().hex[:12]
        message_started = False
        loop = asyncio.get_running_loop()
        deadline = loop.time() + settings.session_timeout
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
        error_sent = False
        try:
            unsubscribe = session.on(on_event)
            await session.send(prompt)

            while not idle_event.is_set():
                if loop.time() >= deadline:
                    logger.warning("AG-UI session idle timeout", extra={"thread_id": thread_id})
                    yield sse_format({"type": "RUN_ERROR", "message": "Session timed out"})
                    error_sent = True
                    await pool.disconnect(thread_id, isolation_session_id=isolation_session_id)
                    break
                try:
                    msg = await asyncio.wait_for(send_queue.get(), timeout=0.1)
                except TimeoutError:
                    continue

                if msg["type"] == "error":
                    yield sse_format({"type": "RUN_ERROR", "message": msg["content"]})
                    error_sent = True
                    break
                elif msg["type"] == "delta":
                    if not message_started:
                        yield sse_format({"type": "TEXT_MESSAGE_START", "message_id": message_id})
                        message_started = True
                    yield sse_format({"type": "TEXT_MESSAGE_CONTENT", "delta": msg["content"]})

            # Drain remaining queued events
            if not error_sent:
                while not send_queue.empty():
                    msg = send_queue.get_nowait()
                    if msg["type"] == "delta":
                        if not message_started:
                            yield sse_format({"type": "TEXT_MESSAGE_START", "message_id": message_id})
                            message_started = True
                        yield sse_format({"type": "TEXT_MESSAGE_CONTENT", "delta": msg["content"]})

            if message_started and not error_sent:
                yield sse_format({"type": "TEXT_MESSAGE_END", "message_id": message_id})

        except Exception:
            logger.exception("Copilot session error; terminating stream")
            yield sse_format({"type": "RUN_ERROR", "message": "An internal error occurred"})
            # On error, disconnect so next request gets a fresh session
            await pool.disconnect(thread_id, isolation_session_id=isolation_session_id)
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


def initialization_error_message(error: RuntimeError, default_message: str) -> str:
    """Return a client-safe initialization error message."""
    if isinstance(error, FoundryConfigurationError):
        return "Foundry BYOK is not configured. Check the server's Azure AI Foundry settings."
    return default_message


@router.post("/v1/files/upload")
async def upload_file(request: Request, file: UploadFile) -> JSONResponse:
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

    isolation_session_id = _resolve_isolation_session_id(request, "upload")
    blob_name = generate_blob_name(filename, isolation_session_id=isolation_session_id)
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
    except Exception as exc:
        return log_and_respond(
            logger,
            502,
            "UPLOAD_FAILED",
            "Failed to upload file to storage",
            "Blob upload failed",
            extra={"upload_filename": filename},
            exception=exc,
        )

    result = UploadResult(
        blob_name=blob_name,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
    )
    return JSONResponse(status_code=200, content=result.model_dump())


@router.delete("/v1/threads/{thread_id}")
async def delete_thread(thread_id: str, request: Request) -> dict[str, str]:
    """Disconnect and clean up a conversation thread."""
    isolation_session_id = _resolve_isolation_session_id(request, thread_id)
    pool = get_session_pool()
    await pool.disconnect(thread_id, isolation_session_id=isolation_session_id)
    foundry_pool = get_foundry_session_pool()
    await foundry_pool.disconnect(thread_id, isolation_session_id=isolation_session_id)
    return {"status": "deleted", "thread_id": thread_id}


@router.post("/v1/threads/{thread_id}/abort")
async def abort_thread(thread_id: str, request: Request) -> dict[str, str]:
    """Abort the active request for a conversation thread.

    Returns status "aborted" for an active session and "not_found" when the
    thread has no active in-memory session to abort.
    """
    isolation_session_id = _resolve_isolation_session_id(request, thread_id)
    pool = get_session_pool()
    aborted = await pool.abort(thread_id, isolation_session_id=isolation_session_id)
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
async def teams_stream(request: TeamsRequest, http_request: Request) -> StreamingResponse:
    """Execute a multi-agent pattern with SSE streaming."""
    if request.pattern_id not in PATTERNS:
        raise HTTPException(status_code=404, detail="Pattern not found")

    prompt = request.prompt
    isolation_session_id = _resolve_isolation_session_id(
        http_request,
        request.thread_id or "teams",
    )
    if request.attachments:
        try:
            file_context = sse_utils.resolve_attachments(
                [att.model_dump() for att in request.attachments],
                isolation_session_id=isolation_session_id,
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        if file_context:
            prompt = file_context + "\n\n" + prompt

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in run_teams(
            request.pattern_id,
            prompt,
            request.max_rounds,
            request.thread_id,
            isolation_session_id=isolation_session_id,
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


@router.get("/v1/models")
async def list_anthropic_models() -> JSONResponse:
    """List models supported by the Anthropic Messages API adapter.

    Returns a list compatible with the Anthropic client's model-listing format
    so Claude Code can confirm the adapter is reachable before sending real
    requests.
    """
    if not settings.anthropic_route_enabled:
        raise HTTPException(status_code=404, detail="Anthropic adapter is disabled")
    from src.runtime.state import get_client
    from src.thirdparty.anthropic_models import AnthropicModelInfo, AnthropicModelListResponse

    try:
        sdk_models = await get_client().list_models()
    except Exception as exc:
        logger.exception("Failed to list models from Copilot SDK")
        raise HTTPException(status_code=502, detail="Could not retrieve model list from Copilot SDK") from exc

    data = [AnthropicModelInfo(id=m.id) for m in sdk_models]
    return JSONResponse(AnthropicModelListResponse(data=data).model_dump())


@router.post("/v1/messages/count_tokens")
async def anthropic_count_tokens_endpoint(request: Request) -> JSONResponse:
    """Approximate the input token count for an Anthropic Messages request.

    Claude Code calls this endpoint during normal session start/turn
    handling. The adapter has no access to Anthropic's real tokenizer, so it
    returns a best-effort character-based estimate rather than 404ing, which
    would otherwise surface to callers as an unexplained connection failure.
    """
    if not settings.anthropic_route_enabled:
        raise HTTPException(status_code=404, detail="Anthropic adapter is disabled")
    from src.thirdparty.anthropic_adapter import estimate_input_tokens
    from src.thirdparty.anthropic_models import (
        AnthropicCountTokensRequest,
        AnthropicCountTokensResponse,
    )

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    try:
        req = AnthropicCountTokensRequest.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    input_tokens = estimate_input_tokens(req)
    return JSONResponse(AnthropicCountTokensResponse(input_tokens=input_tokens).model_dump())


@router.post("/v1/messages", response_model=None)
@router.post("/v1/messages/", response_model=None, include_in_schema=False)
async def anthropic_messages_endpoint(request: Request) -> StreamingResponse | JSONResponse:
    """Anthropic Messages API adapter backed by the Copilot SDK.

    Accepts the Anthropic ``POST /v1/messages`` request format and converts it
    to a Copilot SDK session request.  Streaming (SSE) and non-streaming JSON
    responses are both supported.

    Since callers do not hold a GitHub Apps OAuth session cookie, the Copilot
    SDK session is authenticated with ``THIRDPARTY_GITHUB_PAT`` instead.

    Tool-use bridge: top-level ``tools`` are registered as Copilot SDK tools
    whose handlers block until a matching client-supplied ``tool_result``
    arrives (see src.thirdparty.anthropic_tool_bridge). When the model
    requests one, the turn ends early with a native ``tool_use`` content
    block and ``stop_reason="tool_use"``; the client is expected to reply
    with a new request whose messages include the corresponding
    ``tool_result`` block(s), which resumes the same underlying Copilot SDK
    session/turn rather than starting a new one.

    Minimal agent loop: sessions for this route are created with
    ``minimal_agent_loop=True`` (see ``SessionPool.get_or_create``), so the
    Copilot CLI does not autonomously run its own built-in code-based tools,
    Agent Skills, or repo/user-level config discovery. Only the tools an
    Anthropic client explicitly declares (via the bridge above) are
    available, keeping this route as close to a pure model proxy as the SDK
    allows.

    Remaining Phase 1 limitation (returns explicit 400 rather than silent
    loss): image, document, and thinking content blocks.
    """
    if not settings.anthropic_route_enabled:
        raise HTTPException(status_code=404, detail="Anthropic adapter is disabled")
    from src.thirdparty.anthropic_adapter import (
        extract_system_prompt,
        extract_tool_result_blocks,
        parse_tool_definitions,
        remove_system_messages,
    )
    from src.thirdparty.anthropic_models import (
        AnthropicMessagesRequest,
        AnthropicMessagesResponse,
        AnthropicTextContentBlock,
        AnthropicUsage,
    )
    from src.thirdparty.anthropic_stream import (
        sse_content_block_delta,
        sse_content_block_delta_input_json,
        sse_content_block_start,
        sse_content_block_start_tool_use,
        sse_content_block_stop,
        sse_error,
        sse_message_delta,
        sse_message_start,
        sse_message_stop,
    )
    from src.thirdparty.anthropic_tool_bridge import (
        bridge_key,
        build_bridge_tools,
        resolve_pending_tool_call,
        tool_use_content_block,
    )

    def _validate_tool_aware_messages(parsed_req: AnthropicMessagesRequest) -> None:
        """Reject only the content block types the tool-use bridge still can't handle.

        Unlike the earlier text-only adapter validation, ``tool_use`` and
        ``tool_result`` blocks are supported here by the tool-use bridge.
        """
        for msg in parsed_req.messages:
            if not isinstance(msg.content, list):
                continue
            for block in msg.content:
                btype = block.get("type") if isinstance(block, dict) else None
                if btype in _ANTHROPIC_UNSUPPORTED_BLOCK_TYPES:
                    raise ValueError(
                        f"Unsupported content block type '{btype}' in messages. "
                        "Image, document, and thinking content blocks are not supported."
                    )
                if btype == "text" and not isinstance(block.get("text"), str):
                    raise ValueError("Text content blocks must contain a string 'text' field.")

    def _extract_prompt_text(messages: list[Any]) -> str:
        """Return the text of the most recent user message.

        Non-text blocks (``tool_use``, ``tool_result``) are skipped here;
        ``tool_result`` content is handled separately by resolving pending
        bridged tool calls rather than being folded into the outgoing
        prompt text.
        """
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            raise ValueError("Request contains no user messages.")
        content = user_messages[-1].content
        if isinstance(content, str):
            return content
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type", "text") == "text"
        )

    github_token = _require_thirdparty_github_pat()

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    try:
        req = AnthropicMessagesRequest.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        _validate_tool_aware_messages(req)
        tool_definitions = parse_tool_definitions(req)
        tool_result_blocks = extract_tool_result_blocks(req)
        normalized_messages = remove_system_messages(req)
        prompt = _extract_prompt_text(normalized_messages)
        system_prompt = extract_system_prompt(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Use a stable thread key so the SDK session maintains history across
    # interactive Claude Code turns. Isolation is scoped by the optional
    # client-supplied X-Isolation-Session-ID header, falling back to a
    # shared default namespace when the caller omits it.
    thread_id = "anthropic-v1"
    isolation_session_id = _resolve_isolation_session_id(request, "session")
    bridge_registry_key = bridge_key(isolation_session_id, thread_id)

    message_id = f"msg_{uuid.uuid4().hex[:24]}"

    # Bridge tools are only actually registered with the SDK when this call
    # creates/resumes the underlying session (see SessionPool.get_or_create);
    # an already-cached in-memory session keeps whatever tools it was
    # created with.
    bridge_tools = (
        build_bridge_tools(
            tool_definitions,
            _get_anthropic_tool_bridge_registry(),
            bridge_registry_key,
        )
        if tool_definitions
        else []
    )

    # Acquire and configure the session before branching so that failures
    # (unknown model, auth error, SDK init error) return a proper HTTP error
    # instead of being swallowed inside the SSE stream. Everything through
    # the final response happens while holding the per-thread/isolation
    # turn lock acquired below, so two overlapping requests for the same key
    # can never concurrently use (or disconnect out from under) the same
    # underlying SDK session -- see SessionPool.get_turn_lock().
    pool = get_session_pool()
    turn_lock = pool.get_turn_lock(thread_id, isolation_session_id=isolation_session_id)
    await turn_lock.acquire()
    lock_active = True

    def _release_turn_lock() -> None:
        nonlocal lock_active
        if lock_active:
            lock_active = False
            turn_lock.release()

    # A request carrying tool_result blocks continues a prior tool_use turn
    # on the *same* underlying SDK session. It must never be evicted based
    # on a system-message mismatch (e.g. the client omitting `system` on the
    # follow-up, or resending a slightly different value): doing so would
    # disconnect the session out from under the still-in-flight bridged
    # tool call, cancelling it before it can be resolved below.
    is_tool_result_continuation = bool(tool_result_blocks)

    try:
        try:
            if system_prompt:
                session = await pool.get_or_create(
                    thread_id,
                    github_token,
                    isolation_session_id=isolation_session_id,
                    extra_tools=bridge_tools,
                    system_message=system_prompt,
                    reconcile_system_message=not is_tool_result_continuation,
                    minimal_agent_loop=True,
                )
            else:
                session = await pool.get_or_create(
                    thread_id,
                    github_token,
                    isolation_session_id=isolation_session_id,
                    extra_tools=bridge_tools,
                    reconcile_system_message=not is_tool_result_continuation,
                    minimal_agent_loop=True,
                )
            await session.set_model(req.model)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503, detail=f"Session initialization failed: {exc}"
            ) from exc

        # A request carrying tool_result blocks is a continuation of a prior
        # tool_use turn: resolve the matching pending bridged tool call(s) so
        # the still-awaiting Tool handler(s) can return, instead of sending a
        # new prompt. Fail fast (before starting either response type) if
        # none of the supplied tool_result blocks matched a pending call for
        # this isolation scope/thread.
        send_new_prompt = True
        if tool_result_blocks:
            send_new_prompt = False
            resolved_any = False
            registry = _get_anthropic_tool_bridge_registry()
            for tool_result_block in tool_result_blocks:
                if await resolve_pending_tool_call(
                    registry, bridge_registry_key, tool_result_block
                ):
                    resolved_any = True
            if not resolved_any:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No matching pending tool call(s) found for the "
                        "supplied tool_result block(s)."
                    ),
                )
    except Exception:
        _release_turn_lock()
        raise

    if req.stream:

        async def stream_generator() -> AsyncGenerator[str, None]:
            yield sse_message_start(message_id, req.model)
            yield sse_content_block_start(0)

            output_tokens = 0
            content_block_open = True
            idle_event = asyncio.Event()
            tool_use_event = asyncio.Event()
            tool_use_blocks: list[dict[str, Any]] = []
            send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + settings.session_timeout

            def on_event(event: Any) -> None:
                from copilot.generated.session_events import (
                    AssistantMessageDeltaData,
                    ExternalToolRequestedData,
                    SessionErrorData,
                    SessionIdleData,
                )

                match event.data:
                    case AssistantMessageDeltaData() as delta:
                        loop.call_soon_threadsafe(
                            send_queue.put_nowait,
                            {"type": "delta", "content": delta.delta_content},
                        )
                    case ExternalToolRequestedData() as tool_req:
                        loop.call_soon_threadsafe(
                            send_queue.put_nowait,
                            {
                                "type": "tool_use",
                                "tool_call_id": tool_req.tool_call_id,
                                "tool_name": tool_req.tool_name,
                                "arguments": tool_req.arguments,
                            },
                        )
                        loop.call_soon_threadsafe(tool_use_event.set)
                    case SessionErrorData() as err:
                        loop.call_soon_threadsafe(
                            send_queue.put_nowait,
                            {"type": "error", "content": err.message or "Unknown SDK error"},
                        )
                        loop.call_soon_threadsafe(idle_event.set)
                    case SessionIdleData():
                        loop.call_soon_threadsafe(idle_event.set)

            unsubscribe = None
            error_sent = False
            try:
                unsubscribe = session.on(on_event)
                if send_new_prompt:
                    await session.send(prompt)

                while not idle_event.is_set() and not tool_use_event.is_set():
                    if loop.time() >= deadline:
                        if content_block_open:
                            yield sse_content_block_stop(0)
                            content_block_open = False
                        yield sse_error("server_error", "Session timed out")
                        error_sent = True
                        await pool.disconnect(thread_id, isolation_session_id=isolation_session_id)
                        break
                    try:
                        msg = await asyncio.wait_for(send_queue.get(), timeout=0.1)
                    except TimeoutError:
                        continue
                    if msg["type"] == "error":
                        if content_block_open:
                            yield sse_content_block_stop(0)
                            content_block_open = False
                        yield sse_error("server_error", msg["content"])
                        error_sent = True
                        break
                    if msg["type"] == "delta":
                        text = msg["content"]
                        output_tokens += len(text)
                        yield sse_content_block_delta(text, 0)
                    elif msg["type"] == "tool_use":
                        tool_use_blocks.append(msg)

                if not error_sent:
                    # Drain anything already queued before idle/tool_use fired.
                    while not send_queue.empty():
                        msg = send_queue.get_nowait()
                        if msg["type"] == "delta":
                            text = msg["content"]
                            output_tokens += len(text)
                            yield sse_content_block_delta(text, 0)
                        elif msg["type"] == "tool_use":
                            tool_use_blocks.append(msg)

                    if tool_use_event.is_set():
                        # A single assistant turn may request several tools
                        # in parallel; briefly wait for any further
                        # tool_use events before finalizing (see
                        # _ANTHROPIC_TOOL_USE_GRACE_SECONDS).
                        grace_deadline = loop.time() + _ANTHROPIC_TOOL_USE_GRACE_SECONDS
                        while True:
                            remaining = grace_deadline - loop.time()
                            if remaining <= 0:
                                break
                            try:
                                msg = await asyncio.wait_for(send_queue.get(), timeout=remaining)
                            except TimeoutError:
                                break
                            if msg["type"] == "delta":
                                text = msg["content"]
                                output_tokens += len(text)
                                yield sse_content_block_delta(text, 0)
                            elif msg["type"] == "tool_use":
                                tool_use_blocks.append(msg)

            except Exception:
                logger.exception("Anthropic adapter stream error")
                if content_block_open:
                    yield sse_content_block_stop(0)
                    content_block_open = False
                yield sse_error("server_error", "An internal error occurred")
                await pool.disconnect(
                    thread_id, isolation_session_id=isolation_session_id
                )
                error_sent = True
            finally:
                if unsubscribe:
                    unsubscribe()
                _release_turn_lock()

            if not error_sent:
                if content_block_open:
                    yield sse_content_block_stop(0)
                    content_block_open = False
                if tool_use_blocks:
                    for index, block in enumerate(tool_use_blocks, start=1):
                        yield sse_content_block_start_tool_use(
                            block["tool_call_id"], block["tool_name"], index=index
                        )
                        arguments = block["arguments"] if isinstance(block["arguments"], dict) else {}
                        yield sse_content_block_delta_input_json(json.dumps(arguments), index=index)
                        yield sse_content_block_stop(index)
                    yield sse_message_delta(output_tokens, stop_reason="tool_use")
                else:
                    yield sse_message_delta(output_tokens)
                yield sse_message_stop()

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming: buffer full response then return JSON
    collected: list[str] = []
    tool_use_blocks = []
    idle_event = asyncio.Event()
    tool_use_event = asyncio.Event()
    send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.session_timeout

    def on_event_blocking(event: Any) -> None:
        from copilot.generated.session_events import (
            AssistantMessageDeltaData,
            ExternalToolRequestedData,
            SessionErrorData,
            SessionIdleData,
        )

        match event.data:
            case AssistantMessageDeltaData() as delta:
                loop.call_soon_threadsafe(
                    send_queue.put_nowait,
                    {"type": "delta", "content": delta.delta_content},
                )
            case ExternalToolRequestedData() as tool_req:
                loop.call_soon_threadsafe(
                    send_queue.put_nowait,
                    {
                        "type": "tool_use",
                        "tool_call_id": tool_req.tool_call_id,
                        "tool_name": tool_req.tool_name,
                        "arguments": tool_req.arguments,
                    },
                )
                loop.call_soon_threadsafe(tool_use_event.set)
            case SessionErrorData() as err:
                loop.call_soon_threadsafe(
                    send_queue.put_nowait,
                    {"type": "error", "content": err.message or "Unknown SDK error"},
                )
                loop.call_soon_threadsafe(idle_event.set)
            case SessionIdleData():
                loop.call_soon_threadsafe(idle_event.set)

    unsubscribe = None
    try:
        unsubscribe = session.on(on_event_blocking)
        if send_new_prompt:
            await session.send(prompt)
        while not idle_event.is_set() and not tool_use_event.is_set():
            if loop.time() >= deadline:
                await get_session_pool().disconnect(
                    thread_id, isolation_session_id=isolation_session_id
                )
                raise HTTPException(status_code=504, detail="Session timed out")
            try:
                msg = await asyncio.wait_for(send_queue.get(), timeout=0.1)
            except TimeoutError:
                continue
            if msg["type"] == "error":
                raise HTTPException(status_code=502, detail=msg["content"])
            if msg["type"] == "delta":
                collected.append(msg["content"])
            elif msg["type"] == "tool_use":
                tool_use_blocks.append(msg)

        while not send_queue.empty():
            msg = send_queue.get_nowait()
            if msg["type"] == "delta":
                collected.append(msg["content"])
            elif msg["type"] == "tool_use":
                tool_use_blocks.append(msg)

        if tool_use_event.is_set():
            # See the streaming branch: briefly wait for any further
            # parallel tool_use requests belonging to the same turn.
            grace_deadline = loop.time() + _ANTHROPIC_TOOL_USE_GRACE_SECONDS
            while True:
                remaining = grace_deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    msg = await asyncio.wait_for(send_queue.get(), timeout=remaining)
                except TimeoutError:
                    break
                if msg["type"] == "delta":
                    collected.append(msg["content"])
                elif msg["type"] == "tool_use":
                    tool_use_blocks.append(msg)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Anthropic adapter non-streaming error")
        await pool.disconnect(thread_id, isolation_session_id=isolation_session_id)
        raise HTTPException(status_code=500, detail="An internal error occurred") from exc
    finally:
        if unsubscribe is not None:
            unsubscribe()
        _release_turn_lock()

    full_text = "".join(collected)
    content_blocks: list[Any] = []
    if full_text or not tool_use_blocks:
        content_blocks.append(AnthropicTextContentBlock(text=full_text))
    for tool_use_block in tool_use_blocks:
        content_blocks.append(
            tool_use_content_block(
                tool_use_block["tool_call_id"], tool_use_block["tool_name"], tool_use_block["arguments"]
            )
        )
    response_obj = AnthropicMessagesResponse(
        id=message_id,
        model=req.model,
        content=content_blocks,
        stop_reason="tool_use" if tool_use_blocks else "end_turn",
        usage=AnthropicUsage(output_tokens=len(full_text)),
    )
    return JSONResponse(response_obj.model_dump())


@router.get("/v1/mcp/tools")
async def list_mcp_tools_endpoint() -> list[MCPToolResponse]:
    """List tools available on the configured remote MCP server.

    Returns an empty list when no MCP server URL is configured or when the
    server is unreachable.
    """
    if not settings.mcp_server_url:
        return []

    from src.runtime.mcp_client import list_mcp_tools

    tools = await list_mcp_tools(settings.mcp_server_url)
    return [
        MCPToolResponse(
            name=t.name,
            description=t.description,
            input_schema=t.input_schema,
        )
        for t in tools
    ]
