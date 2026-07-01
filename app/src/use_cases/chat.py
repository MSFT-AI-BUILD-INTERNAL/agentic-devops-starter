"""Use cases for AG-UI chat streaming."""

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
from fastapi import Request
from fastapi.responses import StreamingResponse

import src.sse_utils as sse_utils
from src.config import settings
from src.logging_utils import setup_logging
from src.sse_utils import build_prompt, sse_format
from src.state import FoundrySessionPool, SessionPool

logger = setup_logging(settings.log_level)
sse_utils.set_logger(logger)


async def stream_chat(
    request: Request,
    pool: SessionPool | FoundrySessionPool,
    initialization_error_message: str,
) -> StreamingResponse:
    """Handle an AG-UI chat request against the supplied session pool."""
    input_data = await request.json()
    thread_id: str = input_data.get("thread_id") or uuid.uuid4().hex[:12]
    run_id: str = input_data.get("run_id") or uuid.uuid4().hex[:12]
    messages: list[dict[str, str]] = input_data.get("messages", [])
    attachments: list[dict[str, Any]] | None = input_data.get("attachments")

    prompt = build_prompt(messages, attachments)

    return chat_streaming_response(
        pool,
        thread_id,
        run_id,
        prompt,
        initialization_error_message,
    )


def chat_streaming_response(
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
            await pool.disconnect(thread_id)
        finally:
            if unsubscribe:
                unsubscribe()

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
