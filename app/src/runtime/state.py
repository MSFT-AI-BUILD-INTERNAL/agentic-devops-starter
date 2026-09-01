"""Shared application state for the CopilotClient instance and session pool."""

import asyncio
import os
import time
from typing import Any, Protocol

from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential
from copilot import CopilotClient
from copilot.session import CopilotSession, PermissionHandler
from copilot.tools import Tool

from src.core.config import settings
from src.core.logging_utils import setup_logging
from src.runtime.isolation import (
    build_config_dir,
    build_copilot_session_id,
    build_pool_key,
    normalize_isolation_session_id,
)
from src.runtime.mcp_config import build_mcp_servers_config
from src.runtime.skills import get_disabled_skills, get_skill_directories
from src.runtime.tools import get_registered_tools

logger = setup_logging(settings.log_level)

_client: CopilotClient | None = None
_foundry_credential: DefaultAzureCredential | None = None
_FOUNDRY_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
_FOUNDRY_TOKEN_REFRESH_SKEW_SECONDS = 300


class FoundryConfigurationError(RuntimeError):
    """Raised when Azure AI Foundry BYOK settings are missing or invalid."""


def _get_allowed_tools() -> list[str] | None:
    """Return optional SDK tool allowlist from COPILOT_API_ALLOWED_TOOLS."""
    value = os.environ.get("COPILOT_API_ALLOWED_TOOLS")
    if value is None:
        return None

    non_empty_tools = [tool.strip() for tool in value.split(",") if tool.strip()]
    return non_empty_tools or None


# Built-in SDK tools that expose the host filesystem, shell, or local database.
# These are unsafe to offer when the Copilot SDK is served as a public web
# service and are excluded from every session by default.
_WEB_UNSAFE_TOOLS: tuple[str, ...] = (
    "bash",
    "write_bash",
    "read_bash",
    "stop_bash",
    "list_bash",
    "view",
    "create",
    "edit",
    "grep",
    "glob",
    "sql",
)


def get_excluded_tools() -> list[str] | None:
    """Return the SDK tool denylist applied to every session.

    Controlled by ``COPILOT_API_EXCLUDED_TOOLS`` (comma-separated). When the
    variable is unset the filesystem/shell/database tools in
    :data:`_WEB_UNSAFE_TOOLS` are excluded by default (secure-by-default). A
    blank value explicitly disables the denylist.

    Note: the SDK ignores ``excluded_tools`` whenever an ``available_tools``
    allowlist is also supplied, so the two must not be combined.
    """
    value = os.environ.get("COPILOT_API_EXCLUDED_TOOLS")
    if value is None:
        return list(_WEB_UNSAFE_TOOLS)

    names = [tool.strip() for tool in value.split(",") if tool.strip()]
    return names or None


def _apply_tool_policy(session_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Attach the SDK tool allow/deny policy to *session_kwargs* in place.

    An ``available_tools`` allowlist takes precedence: when configured, the
    SDK ignores ``excluded_tools``, so we only apply one of the two.
    """
    allowed_tools = _get_allowed_tools()
    if allowed_tools is not None:
        # Keep runtime-registered custom tools (including MCP-proxied tools)
        # visible even when a built-in SDK allowlist is configured.
        available_tools = list(allowed_tools)
        for tool in session_kwargs.get("tools", []):
            tool_name = getattr(tool, "name", "")
            if isinstance(tool_name, str) and tool_name and tool_name not in available_tools:
                available_tools.append(tool_name)
        session_kwargs["available_tools"] = available_tools
        return session_kwargs

    excluded_tools = get_excluded_tools()
    if excluded_tools is not None:
        session_kwargs["excluded_tools"] = excluded_tools
    return session_kwargs


class AISessionPool(Protocol):
    """Common interface for all AI provider session pools.

    Concrete implementations (SessionPool, FoundrySessionPool) satisfy this
    protocol structurally — no explicit inheritance required. Routes and
    lifecycle helpers depend on this abstraction, not on the concrete classes.
    """

    async def get_or_create(
        self,
        thread_id: str,
        github_token: str | None = None,
        *,
        isolation_session_id: str | None = None,
        extra_tools: list[Tool] | None = None,
        system_message: str | None = None,
        reconcile_system_message: bool = True,
    ) -> CopilotSession: ...

    def get_turn_lock(
        self, thread_id: str, isolation_session_id: str | None = None
    ) -> asyncio.Lock: ...

    async def disconnect(
        self, thread_id: str, isolation_session_id: str | None = None
    ) -> None: ...

    async def cleanup_idle(self) -> None: ...

    async def shutdown(self) -> None: ...


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
    """Manages persistent CopilotSession instances keyed by isolation session and thread.

    Sessions are kept alive between turns so the Copilot SDK maintains full
    conversation history internally. Idle sessions are disconnected after a
    configurable timeout and resumed on the next request.
    """

    def __init__(self, idle_timeout: float = 120.0) -> None:
        self._sessions: dict[str, CopilotSession] = {}
        self._active_sessions: dict[str, list[CopilotSession]] = {}
        self._last_active: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()
        self._idle_timeout = idle_timeout
        self._system_messages: dict[str, str | None] = {}
        # Separate from `_locks` (which only guards this pool's own
        # get_or_create/disconnect bookkeeping): callers use this lock to
        # serialize an entire request turn (session acquisition through the
        # final send()/response), so that two overlapping requests for the
        # same thread_id/isolation_session_id never concurrently use, or
        # disconnect out from under, the same underlying SDK session.
        self._turn_locks: dict[str, asyncio.Lock] = {}

    def get_turn_lock(
        self, thread_id: str, isolation_session_id: str | None = None
    ) -> asyncio.Lock:
        """Return the lock serializing an entire request turn for this key.

        Must be a distinct lock from the internal pool-mutation lock: a
        caller can legitimately call `disconnect()` (which acquires the
        internal lock) while still holding this turn lock, and reusing the
        same lock object for both purposes would deadlock.
        """
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        lock = self._turn_locks.get(pool_key)
        if lock is None:
            lock = asyncio.Lock()
            self._turn_locks[pool_key] = lock
        return lock

    async def get_or_create(
        self,
        thread_id: str,
        github_token: str | None = None,
        isolation_session_id: str | None = None,
        *,
        extra_tools: list[Tool] | None = None,
        system_message: str | None = None,
        reconcile_system_message: bool = True,
    ) -> CopilotSession:
        """Return an active session for *thread_id*, resuming or creating as needed.

        ``extra_tools`` are only registered when a new SDK session is
        actually created/resumed here; they have no effect when an
        already-cached in-memory session for *thread_id* is returned, since
        the SDK does not support registering additional tools on an existing
        session. Callers that need per-request tools (e.g. the Anthropic
        tool-use bridge) should treat this as best-effort within the
        lifetime of a given session.

        ``reconcile_system_message=False`` skips the system-message
        mismatch check below entirely and always returns a cached session
        as-is. This is required for requests that resume a pending
        tool-use turn (an Anthropic ``tool_result`` continuation): such a
        request may omit ``system`` or send a different value than the
        turn that originally produced the tool_use, and evicting/recreating
        the session in that case would disconnect the still-in-flight SDK
        tool call, cancelling it out from under the caller before it can be
        resolved.

        """
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        sdk_session_id = build_copilot_session_id("chat", isolated_id, thread_id)
        async with self._pool_lock:
            if pool_key not in self._locks:
                self._locks[pool_key] = asyncio.Lock()
            lock = self._locks[pool_key]

        async with lock:
            session = self._sessions.get(pool_key)
            if session is not None:
                if (
                    not reconcile_system_message
                    or system_message == self._system_messages.get(pool_key)
                ):
                    self._last_active[pool_key] = time.monotonic()
                    return session
                # The caller supplied a different system prompt than the one
                # this session was created/resumed with. Reconfiguring the
                # system message on an existing SDK session isn't supported,
                # so disconnect it and fall through to recreate/resume below
                # with the new prompt rather than silently keeping the old one.
                await session.disconnect()
                self._sessions.pop(pool_key, None)
                self._last_active.pop(pool_key, None)

            client = get_client()
            skill_directories = get_skill_directories()
            disabled_skills = get_disabled_skills()
            registered_tools = get_registered_tools()
            session_kwargs: dict[str, Any] = {
                "on_permission_request": PermissionHandler.approve_all,
                "system_message": {
                    "mode": "replace",
                    "content": (
                        f"{_SYSTEM_MESSAGE}\n\n{system_message}"
                        if system_message
                        else _SYSTEM_MESSAGE
                    ),
                },
                "streaming": True,
                "skill_directories": skill_directories,
                "disabled_skills": disabled_skills,
                "tools": [*registered_tools, *(extra_tools or [])],
                "github_token": github_token,
                "config_dir": build_config_dir(settings.session_config_root_dir, isolated_id),
                "mcp_servers": build_mcp_servers_config(),
            }
            _apply_tool_policy(session_kwargs)
            try:
                session = await client.resume_session(
                    sdk_session_id,
                    **session_kwargs,
                )
            except Exception:
                # Session doesn't exist on disk yet — create a new one.
                session = await client.create_session(
                    session_id=sdk_session_id,
                    **session_kwargs,
                )

            self._sessions[pool_key] = session
            self._system_messages[pool_key] = system_message
            self._last_active[pool_key] = time.monotonic()
            return session

    async def register_active_session(
        self,
        thread_id: str,
        session: CopilotSession,
        isolation_session_id: str | None = None,
    ) -> None:
        """Track a transient session as abortable for *thread_id*."""
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        async with self._pool_lock:
            if pool_key not in self._locks:
                self._locks[pool_key] = asyncio.Lock()
            lock = self._locks[pool_key]

        async with lock:
            active_sessions = self._active_sessions.setdefault(pool_key, [])
            if not any(active_session is session for active_session in active_sessions):
                active_sessions.append(session)

    async def unregister_active_session(
        self,
        thread_id: str,
        session: CopilotSession,
        isolation_session_id: str | None = None,
    ) -> None:
        """Stop tracking a transient session for *thread_id*."""
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        async with self._pool_lock:
            lock = self._locks.get(pool_key)
        if lock is None:
            return
        async with lock:
            sessions = self._active_sessions.get(pool_key)
            if not sessions:
                return
            if session in sessions:
                sessions.remove(session)
            if not sessions:
                self._active_sessions.pop(pool_key, None)

    async def disconnect(self, thread_id: str, isolation_session_id: str | None = None) -> None:
        """Disconnect a session (preserves state on disk for later resume).

        The in-memory pool entry is always evicted, even if the underlying
        SDK ``session.disconnect()`` RPC itself fails (e.g. because the CLI
        subprocess already lost/expired the session server-side). Otherwise
        a caller using this method to evict a known-broken cached session
        (see the Anthropic adapter's stale-session recovery) would itself
        raise, leaving the stale entry in place for every subsequent
        request.
        """
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        async with self._pool_lock:
            lock = self._locks.get(pool_key)
        if lock is None:
            return
        async with lock:
            session = self._sessions.pop(pool_key, None)
            self._last_active.pop(pool_key, None)
            self._system_messages.pop(pool_key, None)
            if session is not None:
                try:
                    await session.disconnect()
                except Exception:
                    logger.warning(
                        "Ignoring error while disconnecting an already-evicted session",
                        exc_info=True,
                        extra={"pool_key": pool_key},
                    )

    async def abort(self, thread_id: str, isolation_session_id: str | None = None) -> bool:
        """Abort active requests for a thread."""
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        async with self._pool_lock:
            lock = self._locks.get(pool_key)
        if lock is None:
            return False
        async with lock:
            persistent_session = self._sessions.get(pool_key)
            active_sessions = self._active_sessions.get(pool_key, [])
            sessions_to_abort = list(active_sessions)
            if persistent_session is not None and not any(
                session is persistent_session for session in sessions_to_abort
            ):
                sessions_to_abort.insert(0, persistent_session)

        if not sessions_to_abort:
            return False
        results = await asyncio.gather(
            *(session.abort() for session in sessions_to_abort), return_exceptions=True
        )
        errors = [result for result in results if isinstance(result, Exception)]
        for error in errors:
            logger.error(
                "Failed to abort session for thread %s (%d session(s) requested): %r",
                pool_key,
                len(sessions_to_abort),
                error,
            )
        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise ExceptionGroup(
                f"Failed to abort {len(errors)} sessions for thread {pool_key}", errors
            )
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
            session = self._sessions.pop(tid, None)
            self._last_active.pop(tid, None)
            if session is not None:
                await session.disconnect()

    async def shutdown(self) -> None:
        """Disconnect all sessions (called during app shutdown)."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            session = self._sessions.pop(session_id, None)
            self._last_active.pop(session_id, None)
            if session is not None:
                await session.disconnect()


class FoundrySessionPool:
    """Manages Azure AI Foundry BYOK sessions isolated from Copilot sessions."""

    def __init__(self, idle_timeout: float = 120.0) -> None:
        self._sessions: dict[str, CopilotSession] = {}
        self._last_active: dict[str, float] = {}
        self._token_expires_on: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()
        self._idle_timeout = idle_timeout
        self._turn_locks: dict[str, asyncio.Lock] = {}

    def get_turn_lock(
        self, thread_id: str, isolation_session_id: str | None = None
    ) -> asyncio.Lock:
        """Return the lock serializing an entire request turn for this key.

        See `SessionPool.get_turn_lock` for why this must be a separate lock
        from the internal pool-mutation lock.
        """
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        lock = self._turn_locks.get(pool_key)
        if lock is None:
            lock = asyncio.Lock()
            self._turn_locks[pool_key] = lock
        return lock

    async def get_or_create(
        self,
        thread_id: str,
        github_token: str | None = None,
        isolation_session_id: str | None = None,
        *,
        extra_tools: list[Tool] | None = None,
        system_message: str | None = None,
        reconcile_system_message: bool = True,
    ) -> CopilotSession:
        """Return an active Foundry BYOK session for *thread_id*.

        ``github_token`` is accepted for interface compatibility with
        :class:`AISessionPool` but is unused; Foundry BYOK authenticates
        via Azure credentials configured on the server. ``extra_tools`` is
        only registered when this call actually creates the session. When
        provided, ``system_message`` is appended to the Foundry system
        context for interface compatibility with :class:`AISessionPool`.
        ``reconcile_system_message`` is accepted for interface compatibility
        with :class:`AISessionPool` but is unused here: this pool never
        evicts a cached session on a system-message mismatch (only on token
        expiry), so there is nothing to opt out of.
        """
        _validate_foundry_settings()
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        sdk_session_id = build_copilot_session_id("foundry", isolated_id, thread_id)
        async with self._pool_lock:
            if pool_key not in self._locks:
                self._locks[pool_key] = asyncio.Lock()
            lock = self._locks[pool_key]

        async with lock:
            session = self._sessions.get(pool_key)
            if session is not None:
                if not self._is_token_expiring(pool_key):
                    self._last_active[pool_key] = time.monotonic()
                    return session
                self._sessions.pop(pool_key, None)
                self._last_active.pop(pool_key, None)
                self._token_expires_on.pop(pool_key, None)
                await session.disconnect()

            client = get_client()
            provider, token_expires_on = _build_foundry_provider()
            skill_directories = get_skill_directories()
            registered_tools = get_registered_tools()
            session_kwargs: dict[str, Any] = {
                "session_id": sdk_session_id,
                "on_permission_request": PermissionHandler.approve_all,
                "system_message": {
                    "mode": "replace",
                    "content": (
                        f"{_FOUNDRY_SYSTEM_MESSAGE}\n\n{system_message}"
                        if system_message
                        else _FOUNDRY_SYSTEM_MESSAGE
                    ),
                },
                "streaming": True,
                "skill_directories": skill_directories,
                "disabled_skills": get_disabled_skills(),
                "tools": [*registered_tools, *(extra_tools or [])],
                "model": settings.azure_ai_model_deployment_name,
                "provider": provider,
                "config_dir": build_config_dir(settings.session_config_root_dir, isolated_id),
                "mcp_servers": build_mcp_servers_config(),
            }
            _apply_tool_policy(session_kwargs)
            session = await client.create_session(**session_kwargs)

            self._sessions[pool_key] = session
            self._last_active[pool_key] = time.monotonic()
            if token_expires_on is not None:
                self._token_expires_on[pool_key] = token_expires_on
            return session

    async def disconnect(self, thread_id: str, isolation_session_id: str | None = None) -> None:
        """Disconnect a Foundry BYOK session.

        The in-memory pool entry is always evicted even if the underlying
        SDK ``session.disconnect()`` RPC itself fails (e.g. because the CLI
        subprocess already lost/expired the session server-side).
        """
        isolated_id = normalize_isolation_session_id(isolation_session_id, thread_id)
        pool_key = build_pool_key(isolated_id, thread_id)
        async with self._pool_lock:
            lock = self._locks.get(pool_key)
        if lock is None:
            return
        async with lock:
            session = self._sessions.pop(pool_key, None)
            self._last_active.pop(pool_key, None)
            self._token_expires_on.pop(pool_key, None)
            if session is not None:
                try:
                    await session.disconnect()
                except Exception:
                    logger.warning(
                        "Ignoring error while disconnecting an already-evicted session",
                        exc_info=True,
                        extra={"pool_key": pool_key},
                    )

    async def cleanup_idle(self) -> None:
        """Disconnect sessions that have been idle longer than the timeout."""
        now = time.monotonic()
        to_disconnect: list[str] = []

        async with self._pool_lock:
            for tid, last in list(self._last_active.items()):
                if now - last > self._idle_timeout:
                    to_disconnect.append(tid)

        for tid in to_disconnect:
            session = self._sessions.pop(tid, None)
            self._last_active.pop(tid, None)
            self._token_expires_on.pop(tid, None)
            if session is not None:
                await session.disconnect()

    async def shutdown(self) -> None:
        """Disconnect all Foundry BYOK sessions."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            session = self._sessions.pop(session_id, None)
            self._last_active.pop(session_id, None)
            self._token_expires_on.pop(session_id, None)
            if session is not None:
                await session.disconnect()

    def _is_token_expiring(self, pool_key: str) -> bool:
        """Return whether an Azure Identity bearer token needs session renewal."""
        expires_on = self._token_expires_on.get(pool_key)
        if expires_on is None:
            return False
        return expires_on <= int(time.time()) + _FOUNDRY_TOKEN_REFRESH_SKEW_SECONDS


def _validate_foundry_settings() -> None:
    """Ensure Foundry BYOK settings are present before opening a BYOK session."""
    missing = []
    if not settings.azure_ai_project_endpoint:
        missing.append("AZURE_AI_PROJECT_ENDPOINT")
    if not settings.azure_ai_model_deployment_name:
        missing.append("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if _resolve_foundry_auth_mode() == "api_key" and not settings.foundry_api_key:
        missing.append("FOUNDRY_API_KEY or AZURE_OPENAI_API_KEY")
    if missing:
        raise FoundryConfigurationError(
            f"Foundry BYOK is not configured: missing {', '.join(missing)}"
        )
    if settings.foundry_wire_api not in {"responses", "completions"}:
        raise FoundryConfigurationError(
            "Foundry BYOK is not configured: FOUNDRY_WIRE_API must be responses or completions"
        )


def _resolve_foundry_auth_mode() -> str:
    """Return the concrete Foundry auth mode for the current settings."""
    auth_mode = settings.foundry_auth_mode.lower()
    if auth_mode not in {"auto", "api_key", "azure_identity"}:
        raise FoundryConfigurationError(
            "Foundry BYOK is not configured: FOUNDRY_AUTH_MODE must be auto, api_key, "
            "or azure_identity"
        )
    if auth_mode == "auto":
        return "api_key" if settings.foundry_api_key else "azure_identity"
    return auth_mode


def _build_foundry_provider() -> tuple[dict[str, Any], int | None]:
    """Build Copilot SDK provider config for Azure AI Foundry BYOK."""
    provider: dict[str, Any] = {
        "type": "openai",
        "base_url": _normalize_foundry_base_url(settings.azure_ai_project_endpoint),
        "wire_api": settings.foundry_wire_api,
    }
    if _resolve_foundry_auth_mode() == "api_key":
        provider["api_key"] = settings.foundry_api_key
        return provider, None

    token = _get_foundry_bearer_token()
    provider["bearer_token"] = token.token
    return provider, token.expires_on


def _get_foundry_bearer_token() -> AccessToken:
    """Get an Azure AI bearer token via Azure CLI locally or Managed Identity in production."""
    global _foundry_credential
    if _foundry_credential is None:
        _foundry_credential = DefaultAzureCredential()
    try:
        return _foundry_credential.get_token(_FOUNDRY_TOKEN_SCOPE)
    except (CredentialUnavailableError, ClientAuthenticationError) as error:
        raise FoundryConfigurationError(
            "Foundry BYOK is not configured: Azure Identity authentication failed"
        ) from error


def _normalize_foundry_base_url(endpoint: str) -> str:
    """Return the OpenAI-compatible Foundry base URL expected by the SDK."""
    normalized = endpoint.rstrip("/")
    if normalized.endswith("/openai/v1"):
        return f"{normalized}/"
    return f"{normalized}/openai/v1/"


# Shared constants
_SYSTEM_MESSAGE = (
    "You are a helpful AI assistant powered by GitHub Copilot. "
    "Provide clear, accurate, and well-structured responses."
)
_FOUNDRY_SYSTEM_MESSAGE = (
    "You are a helpful AI assistant powered by Azure AI Foundry BYOK. "
    "Provide clear, accurate, and well-structured responses."
)


# Module-level singleton — initialized during app lifespan.
_session_pool: SessionPool | None = None
_foundry_session_pool: FoundrySessionPool | None = None


def set_session_pool(pool: SessionPool) -> None:
    """Store the shared SessionPool instance."""
    global _session_pool
    _session_pool = pool


def get_session_pool() -> SessionPool:
    """Retrieve the shared SessionPool instance."""
    if _session_pool is None:
        raise RuntimeError("SessionPool not initialized")
    return _session_pool


def set_foundry_session_pool(pool: FoundrySessionPool) -> None:
    """Store the shared Foundry BYOK SessionPool instance."""
    global _foundry_session_pool
    _foundry_session_pool = pool


def get_foundry_session_pool() -> FoundrySessionPool:
    """Retrieve the shared Foundry BYOK SessionPool instance."""
    if _foundry_session_pool is None:
        raise RuntimeError("FoundrySessionPool not initialized")
    return _foundry_session_pool
