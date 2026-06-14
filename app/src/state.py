"""Shared application state for the CopilotClient instance and session pool."""

import asyncio
import os
import time
from typing import Any

from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential
from copilot import CopilotClient
from copilot.session import CopilotSession, PermissionHandler

from src.config import settings
from src.skills import get_disabled_skills, get_skill_directories

_client: CopilotClient | None = None
_foundry_credential: DefaultAzureCredential | None = None
_FOUNDRY_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
_FOUNDRY_TOKEN_REFRESH_SKEW_SECONDS = 300


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
            session_kwargs: dict[str, Any] = {
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


class FoundrySessionPool:
    """Manages Azure AI Foundry BYOK sessions isolated from Copilot sessions."""

    def __init__(self, idle_timeout: float = 120.0) -> None:
        self._sessions: dict[str, CopilotSession] = {}
        self._last_active: dict[str, float] = {}
        self._token_expires_on: dict[str, int] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()
        self._idle_timeout = idle_timeout

    async def get_or_create(self, thread_id: str) -> CopilotSession:
        """Return an active Foundry BYOK session for *thread_id*."""
        _validate_foundry_settings()
        async with self._pool_lock:
            if thread_id not in self._locks:
                self._locks[thread_id] = asyncio.Lock()
            lock = self._locks[thread_id]

        async with lock:
            session = self._sessions.get(thread_id)
            if session is not None:
                if not self._is_token_expiring(thread_id):
                    self._last_active[thread_id] = time.monotonic()
                    return session
                self._sessions.pop(thread_id, None)
                self._last_active.pop(thread_id, None)
                self._token_expires_on.pop(thread_id, None)
                await session.disconnect()

            client = get_client()
            allowed_tools = _get_allowed_tools()
            provider, token_expires_on = _build_foundry_provider()
            session_kwargs: dict[str, Any] = {
                "session_id": f"foundry-{thread_id}",
                "on_permission_request": PermissionHandler.approve_all,
                "system_message": {"mode": "replace", "content": _FOUNDRY_SYSTEM_MESSAGE},
                "streaming": True,
                "skill_directories": get_skill_directories(),
                "disabled_skills": get_disabled_skills(),
                "model": settings.azure_ai_model_deployment_name,
                "provider": provider,
            }
            if allowed_tools is not None:
                session_kwargs["available_tools"] = allowed_tools
            session = await client.create_session(**session_kwargs)

            self._sessions[thread_id] = session
            self._last_active[thread_id] = time.monotonic()
            if token_expires_on is not None:
                self._token_expires_on[thread_id] = token_expires_on
            return session

    async def disconnect(self, thread_id: str) -> None:
        """Disconnect a Foundry BYOK session."""
        async with self._pool_lock:
            lock = self._locks.get(thread_id)
        if lock is None:
            return
        async with lock:
            session = self._sessions.pop(thread_id, None)
            self._last_active.pop(thread_id, None)
            self._token_expires_on.pop(thread_id, None)
            if session is not None:
                await session.disconnect()

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
        """Disconnect all Foundry BYOK sessions."""
        thread_ids = list(self._sessions.keys())
        for tid in thread_ids:
            await self.disconnect(tid)

    def _is_token_expiring(self, thread_id: str) -> bool:
        """Return whether an Azure Identity bearer token needs session renewal."""
        expires_on = self._token_expires_on.get(thread_id)
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
        raise RuntimeError(f"Foundry BYOK is not configured: missing {', '.join(missing)}")
    if settings.foundry_wire_api not in {"responses", "completions"}:
        raise RuntimeError(
            "Foundry BYOK is not configured: FOUNDRY_WIRE_API must be responses or completions"
        )


def _resolve_foundry_auth_mode() -> str:
    """Return the concrete Foundry auth mode for the current settings."""
    auth_mode = settings.foundry_auth_mode.lower()
    if auth_mode not in {"auto", "api_key", "azure_identity"}:
        raise RuntimeError(
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
        raise RuntimeError("Foundry BYOK is not configured: Azure Identity authentication failed") from error


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
