"""Shared application state for the CopilotClient instance and session pool."""

import asyncio
import os
import time

from copilot import CopilotClient
from copilot.session import CopilotSession, PermissionHandler

from src.skills import get_disabled_skills, get_skill_directories

_client: CopilotClient | None = None


def _get_allowed_tools() -> list[str] | None:
    """Return optional SDK tool allowlist from COPILOT_API_ALLOWED_TOOLS."""
    value = os.environ.get("COPILOT_API_ALLOWED_TOOLS")
    if value is None:
        return None

    non_empty_tools = [tool.strip() for tool in value.split(",") if tool.strip()]
    return non_empty_tools or None


def set_client(client: CopilotClient) -> None:
    """Store the shared CopilotClient instance."""
    global _client
    _client = client


def get_client() -> CopilotClient:
    """Retrieve the shared CopilotClient instance."""
    if _client is None:
        raise RuntimeError("CopilotClient not initialized")
    return _client


class SessionPool:
    """Manages persistent CopilotSession instances keyed by thread_id.

    Sessions are kept alive between turns so the Copilot SDK maintains full
    conversation history internally. Idle sessions are disconnected after a
    configurable timeout and resumed on the next request.
    """

    def __init__(self, idle_timeout: float = 120.0) -> None:
        self._sessions: dict[str, CopilotSession] = {}
        self._last_active: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()
        self._idle_timeout = idle_timeout

    async def get_or_create(self, thread_id: str) -> CopilotSession:
        """Return an active session for *thread_id*, resuming or creating as needed."""
        async with self._pool_lock:
            if thread_id not in self._locks:
                self._locks[thread_id] = asyncio.Lock()
            lock = self._locks[thread_id]

        async with lock:
            session = self._sessions.get(thread_id)
            if session is not None:
                self._last_active[thread_id] = time.monotonic()
                return session

            client = get_client()
            github_token = os.environ.get("GITHUB_TOKEN")
            skill_directories = get_skill_directories()
            disabled_skills = get_disabled_skills()
            allowed_tools = _get_allowed_tools()
            session_kwargs = {
                "on_permission_request": PermissionHandler.approve_all,
                "system_message": {"mode": "replace", "content": _SYSTEM_MESSAGE},
                "streaming": True,
                "skill_directories": skill_directories,
                "disabled_skills": disabled_skills,
                "github_token": github_token,
            }
            if allowed_tools is not None:
                session_kwargs["available_tools"] = allowed_tools
            try:
                session = await client.resume_session(
                    thread_id,
                    **session_kwargs,
                )
            except Exception:
                # Session doesn't exist on disk yet — create a new one.
                session = await client.create_session(
                    session_id=thread_id,
                    **session_kwargs,
                )

            self._sessions[thread_id] = session
            self._last_active[thread_id] = time.monotonic()
            return session

    async def disconnect(self, thread_id: str) -> None:
        """Disconnect a session (preserves state on disk for later resume)."""
        async with self._pool_lock:
            lock = self._locks.get(thread_id)
        if lock is None:
            return
        async with lock:
            session = self._sessions.pop(thread_id, None)
            self._last_active.pop(thread_id, None)
            if session is not None:
                await session.disconnect()

    async def abort(self, thread_id: str) -> bool:
        """Abort the active request for a session."""
        async with self._pool_lock:
            lock = self._locks.get(thread_id)
        if lock is None:
            return False
        async with lock:
            session = self._sessions.get(thread_id)
            if session is None:
                return False
            await session.abort()
            self._last_active[thread_id] = time.monotonic()
            return True

    async def cleanup_idle(self) -> None:
        """Disconnect sessions that have been idle longer than the timeout."""
        now = time.monotonic()
        to_disconnect: list[str] = []

        async with self._pool_lock:
            for tid, last in list(self._last_active.items()):
                if now - last > self._idle_timeout:
                    to_disconnect.append(tid)

        for tid in to_disconnect:
            await self.disconnect(tid)

    async def shutdown(self) -> None:
        """Disconnect all sessions (called during app shutdown)."""
        thread_ids = list(self._sessions.keys())
        for tid in thread_ids:
            await self.disconnect(tid)


# Shared constants
_SYSTEM_MESSAGE = (
    "You are a helpful AI assistant powered by GitHub Copilot. "
    "Provide clear, accurate, and well-structured responses."
)


# Module-level singleton — initialized during app lifespan.
_session_pool: SessionPool | None = None


def set_session_pool(pool: SessionPool) -> None:
    """Store the shared SessionPool instance."""
    global _session_pool
    _session_pool = pool


def get_session_pool() -> SessionPool:
    """Retrieve the shared SessionPool instance."""
    if _session_pool is None:
        raise RuntimeError("SessionPool not initialized")
    return _session_pool
