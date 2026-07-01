"""Tests for session creation skill configuration."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast

import pytest
from azure.core.credentials import AccessToken

import src.runtime.skills as skills_module
import src.runtime.state as state_module
from src.runtime.skills import load_skills
from src.runtime.state import FoundrySessionPool, SessionPool, set_client


class _FakeSession:
    def __init__(self) -> None:
        self.abort_count = 0

    async def abort(self) -> None:
        self.abort_count += 1

    async def disconnect(self) -> None:
        pass


class _FailingAbortSession(_FakeSession):
    async def abort(self) -> None:
        self.abort_count += 1
        raise RuntimeError("abort failed")


class _FakeClient:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, Any] | None = None

    async def resume_session(self, *_args: Any, **_kwargs: Any) -> _FakeSession:
        raise RuntimeError("no saved session")

    async def create_session(self, **kwargs: Any) -> _FakeSession:
        self.create_kwargs = kwargs
        return _FakeSession()


@pytest.fixture(autouse=True)
def isolate_skills_and_client(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    monkeypatch.setattr(skills_module, "_skill_directories", [])
    monkeypatch.setattr(skills_module, "_loaded_skill_names", [])
    monkeypatch.setattr(state_module, "_client", None)
    monkeypatch.setattr(state_module.settings, "foundry_auth_mode", "auto")
    yield


@pytest.mark.asyncio
async def test_session_pool_enables_sdk_skills_when_directories_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Copilot SDK must receive skill directories using supported kwargs."""
    client = _FakeClient()
    monkeypatch.delenv("COPILOT_API_SKILL_DIRECTORIES", raising=False)
    skill_directories = load_skills()
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-with-skills")

        assert client.create_kwargs is not None
        assert "enable_skills" not in client.create_kwargs
        assert client.create_kwargs["skill_directories"] == skill_directories
        allowlist = client.create_kwargs.get("available_tools")
        # An empty available_tools allowlist disables every tool (including the
        # skill-loading tool), which silently neutralizes skills. Guard against it.
        assert allowlist is None or len(allowlist) > 0
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_standard_session_pool_does_not_use_byok_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default GitHub Copilot sessions must not receive BYOK provider config."""
    client = _FakeClient()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("standard-thread")

        assert client.create_kwargs is not None
        assert client.create_kwargs["session_id"] == "standard-thread"
        assert "provider" not in client.create_kwargs
        assert "model" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_foundry_session_pool_uses_isolated_byok_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foundry sessions must use a prefixed session id and BYOK provider only."""
    client = _FakeClient()
    monkeypatch.setattr(
        state_module.settings,
        "azure_ai_project_endpoint",
        "https://example.openai.azure.com",
    )
    monkeypatch.setattr(state_module.settings, "azure_ai_model_deployment_name", "gpt-5.2-codex")
    monkeypatch.setattr(state_module.settings, "foundry_api_key", "test-foundry-key")
    monkeypatch.setattr(state_module.settings, "foundry_wire_api", "responses")
    set_client(cast(Any, client))

    pool = FoundrySessionPool()
    try:
        await pool.get_or_create("shared-thread")

        assert client.create_kwargs is not None
        assert client.create_kwargs["session_id"] == "foundry-shared-thread"
        assert client.create_kwargs["model"] == "gpt-5.2-codex"
        assert client.create_kwargs["provider"] == {
            "type": "openai",
            "base_url": "https://example.openai.azure.com/openai/v1/",
            "wire_api": "responses",
            "api_key": "test-foundry-key",
        }
        assert "github_token" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_foundry_session_pool_uses_azure_identity_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foundry sessions may authenticate with Azure CLI or Managed Identity."""
    client = _FakeClient()
    monkeypatch.setattr(
        state_module.settings,
        "azure_ai_project_endpoint",
        "https://example.openai.azure.com",
    )
    monkeypatch.setattr(state_module.settings, "azure_ai_model_deployment_name", "gpt-5.2-codex")
    monkeypatch.setattr(state_module.settings, "foundry_api_key", "")
    monkeypatch.setattr(state_module.settings, "foundry_auth_mode", "azure_identity")
    monkeypatch.setattr(state_module.settings, "foundry_wire_api", "responses")
    monkeypatch.setattr(
        state_module,
        "_get_foundry_bearer_token",
        lambda: AccessToken("test-bearer-token", int(state_module.time.time()) + 3600),
    )
    set_client(cast(Any, client))

    pool = FoundrySessionPool()
    try:
        await pool.get_or_create("managed-identity-thread")

        assert client.create_kwargs is not None
        assert client.create_kwargs["provider"] == {
            "type": "openai",
            "base_url": "https://example.openai.azure.com/openai/v1/",
            "wire_api": "responses",
            "bearer_token": "test-bearer-token",
        }
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_passes_tool_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When configured, only the configured SDK tools are allowlisted."""
    client = _FakeClient()
    monkeypatch.setenv("COPILOT_API_ALLOWED_TOOLS", "bash, read_file ,")
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-with-tool-allowlist")

        assert client.create_kwargs is not None
        assert client.create_kwargs["available_tools"] == ["bash", "read_file"]
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_omits_empty_tool_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank COPILOT_API_ALLOWED_TOOLS should not pass an empty allowlist."""
    client = _FakeClient()
    monkeypatch.setenv("COPILOT_API_ALLOWED_TOOLS", "  ,   ")
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-with-empty-tool-allowlist")

        assert client.create_kwargs is not None
        assert "available_tools" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_abort_invokes_session_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    """Abort should stop the active request without disconnecting the session."""
    client = _FakeClient()
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        session = cast(_FakeSession, await pool.get_or_create("thread-to-abort"))

        aborted = await pool.abort("thread-to-abort")

        assert aborted is True
        assert session.abort_count == 1
        assert await pool.get_or_create("thread-to-abort") is session
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_abort_missing_thread_returns_false() -> None:
    """Abort should be a no-op when the thread has no active session."""
    pool = SessionPool()

    assert await pool.abort("missing-thread") is False


@pytest.mark.asyncio
async def test_session_pool_abort_invokes_registered_active_sessions() -> None:
    """Abort should stop transient sessions registered for a thread."""
    pool = SessionPool()
    sessions = [_FakeSession(), _FakeSession()]

    for session in sessions:
        await pool.register_active_session("team-thread", cast(Any, session))

    try:
        assert await pool.abort("team-thread") is True
        assert [session.abort_count for session in sessions] == [1, 1]
    finally:
        for session in sessions:
            await pool.unregister_active_session("team-thread", cast(Any, session))


@pytest.mark.asyncio
async def test_session_pool_abort_attempts_all_sessions_on_failure() -> None:
    """Abort should try every active session before reporting failure."""
    pool = SessionPool()
    failing_session = _FailingAbortSession()
    healthy_session = _FakeSession()

    await pool.register_active_session("team-thread", cast(Any, failing_session))
    await pool.register_active_session("team-thread", cast(Any, healthy_session))

    try:
        with pytest.raises(RuntimeError, match="abort failed"):
            await pool.abort("team-thread")
        assert failing_session.abort_count == 1
        assert healthy_session.abort_count == 1
    finally:
        await pool.unregister_active_session("team-thread", cast(Any, failing_session))
        await pool.unregister_active_session("team-thread", cast(Any, healthy_session))


@pytest.mark.asyncio
async def test_session_pool_abort_reports_multiple_failures() -> None:
    """Abort should report every failure when multiple sessions fail."""
    pool = SessionPool()
    sessions = [_FailingAbortSession(), _FailingAbortSession()]

    for session in sessions:
        await pool.register_active_session("team-thread", cast(Any, session))

    try:
        with pytest.raises(ExceptionGroup, match="Failed to abort 2 sessions"):
            await pool.abort("team-thread")
        assert [session.abort_count for session in sessions] == [1, 1]
    finally:
        for session in sessions:
            await pool.unregister_active_session("team-thread", cast(Any, session))
