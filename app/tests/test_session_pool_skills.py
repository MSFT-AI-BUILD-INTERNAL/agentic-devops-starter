"""Tests for session creation skill configuration."""

from __future__ import annotations

import asyncio
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


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


class _FailingAbortSession(_FakeSession):
    async def abort(self) -> None:
        self.abort_count += 1
        raise RuntimeError("abort failed")


class _FailingDisconnectSession(_FakeSession):
    async def disconnect(self) -> None:
        raise RuntimeError("disconnect failed: session already gone server-side")


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
    monkeypatch.delenv("COPILOT_API_ALLOWED_TOOLS", raising=False)
    monkeypatch.delenv("COPILOT_API_EXCLUDED_TOOLS", raising=False)
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
        assert client.create_kwargs["session_id"].startswith("chat-standard-thread-")
        assert "provider" not in client.create_kwargs
        assert "model" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_standard_session_pool_uses_authenticated_user_token() -> None:
    """Standard Copilot sessions use the OAuth token supplied for the user."""
    client = _FakeClient()
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("oauth-thread", github_token="user-token")

        assert client.create_kwargs is not None
        assert client.create_kwargs["github_token"] == "user-token"
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
        await pool.get_or_create("shared-thread", system_message="Use concise answers.")

        assert client.create_kwargs is not None
        assert client.create_kwargs["session_id"].startswith("foundry-shared-thread-")
        assert client.create_kwargs["model"] == "gpt-5.2-codex"
        assert client.create_kwargs["system_message"] == {
            "mode": "replace",
            "content": f"{state_module._FOUNDRY_SYSTEM_MESSAGE}\n\nUse concise answers.",
        }
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
        assert client.create_kwargs["available_tools"] == [
            "bash",
            "read_file",
            "transform_text",
            "fetch_github_zen",
        ]
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_excludes_unsafe_tools_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset COPILOT_API_EXCLUDED_TOOLS must exclude the web-unsafe tool set."""
    client = _FakeClient()
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-default-denylist")

        assert client.create_kwargs is not None
        assert client.create_kwargs["excluded_tools"] == list(state_module._WEB_UNSAFE_TOOLS)
        assert "available_tools" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_uses_custom_tool_denylist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured COPILOT_API_EXCLUDED_TOOLS value overrides the default."""
    client = _FakeClient()
    monkeypatch.setenv("COPILOT_API_EXCLUDED_TOOLS", "bash, sql ,")
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-custom-denylist")

        assert client.create_kwargs is not None
        assert client.create_kwargs["excluded_tools"] == ["bash", "sql"]
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_omits_blank_tool_denylist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blank COPILOT_API_EXCLUDED_TOOLS disables the denylist entirely."""
    client = _FakeClient()
    monkeypatch.setenv("COPILOT_API_EXCLUDED_TOOLS", "  ,  ")
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-blank-denylist")

        assert client.create_kwargs is not None
        assert "excluded_tools" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_allowlist_takes_precedence_over_denylist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """available_tools must win; excluded_tools is ignored by the SDK when both set."""
    client = _FakeClient()
    monkeypatch.setenv("COPILOT_API_ALLOWED_TOOLS", "read_file")
    monkeypatch.setenv("COPILOT_API_EXCLUDED_TOOLS", "bash")
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-allowlist-precedence")

        assert client.create_kwargs is not None
        assert client.create_kwargs["available_tools"] == [
            "read_file",
            "transform_text",
            "fetch_github_zen",
        ]
        assert "excluded_tools" not in client.create_kwargs
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_allowlist_keeps_custom_runtime_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allowlist mode must still keep runtime custom tools visible to the model."""
    client = _FakeClient()
    monkeypatch.setenv("COPILOT_API_ALLOWED_TOOLS", "read_file")
    monkeypatch.setattr(
        state_module,
        "get_registered_tools",
        lambda: [_FakeTool("transform_text"), _FakeTool("mcp_remote_tool")],
    )
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-allowlist-custom-tools")

        assert client.create_kwargs is not None
        assert client.create_kwargs["available_tools"] == [
            "read_file",
            "transform_text",
            "mcp_remote_tool",
        ]
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_registers_code_based_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session creation should include registered code-based tool handlers."""
    client = _FakeClient()
    monkeypatch.delenv("COPILOT_API_ALLOWED_TOOLS", raising=False)
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        await pool.get_or_create("thread-with-runtime-tools")

        assert client.create_kwargs is not None
        tool_names = [tool.name for tool in client.create_kwargs["tools"]]
        assert "transform_text" in tool_names
        assert "fetch_github_zen" in tool_names
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_session_pool_minimal_agent_loop_omits_builtin_tools_and_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """minimal_agent_loop=True must strip built-in tools/skills and disable
    repo/user config discovery, keeping only caller-supplied extra_tools --
    this is what makes the third-party Anthropic adapter behave close to a
    pure model proxy instead of running the SDK's own autonomous tool/skill
    loop."""
    client = _FakeClient()
    monkeypatch.delenv("COPILOT_API_ALLOWED_TOOLS", raising=False)
    skill_directories = load_skills()
    assert skill_directories, "test fixture expects at least one skill directory"
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        bridge_tool = _FakeTool("client_declared_tool")
        await pool.get_or_create(
            "thread-minimal-agent-loop",
            extra_tools=cast(Any, [bridge_tool]),
            minimal_agent_loop=True,
        )

        assert client.create_kwargs is not None
        tool_names = [tool.name for tool in client.create_kwargs["tools"]]
        assert tool_names == ["client_declared_tool"]
        assert client.create_kwargs["skill_directories"] == []
        assert client.create_kwargs["enable_config_discovery"] is False
        assert client.create_kwargs["mcp_servers"] == {}
    finally:
        await pool.shutdown()


@pytest.mark.asyncio
async def test_foundry_session_pool_minimal_agent_loop_omits_builtin_tools_and_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FoundrySessionPool must honor minimal_agent_loop identically to SessionPool."""
    client = _FakeClient()
    monkeypatch.delenv("COPILOT_API_ALLOWED_TOOLS", raising=False)
    monkeypatch.setattr(
        state_module.settings,
        "azure_ai_project_endpoint",
        "https://example.openai.azure.com",
    )
    monkeypatch.setattr(state_module.settings, "azure_ai_model_deployment_name", "gpt-5.2-codex")
    monkeypatch.setattr(state_module.settings, "foundry_api_key", "test-key")
    monkeypatch.setattr(state_module.settings, "foundry_auth_mode", "api_key")
    monkeypatch.setattr(state_module.settings, "foundry_wire_api", "responses")
    skill_directories = load_skills()
    assert skill_directories, "test fixture expects at least one skill directory"
    set_client(cast(Any, client))

    pool = FoundrySessionPool()
    bridge_tool = _FakeTool("client_declared_tool")
    await pool.get_or_create(
        "thread-minimal-agent-loop",
        extra_tools=cast(Any, [bridge_tool]),
        minimal_agent_loop=True,
    )

    assert client.create_kwargs is not None
    tool_names = [tool.name for tool in client.create_kwargs["tools"]]
    assert tool_names == ["client_declared_tool"]
    assert client.create_kwargs["skill_directories"] == []
    assert client.create_kwargs["enable_config_discovery"] is False
    assert client.create_kwargs["mcp_servers"] == {}


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
async def test_session_pool_disconnect_evicts_cache_even_if_sdk_disconnect_fails() -> None:
    """disconnect() must still evict the in-memory session even when the underlying
    SDK disconnect RPC fails (e.g. because the server already lost the session)."""

    class _FailingDisconnectClient(_FakeClient):
        async def create_session(self, **kwargs: Any) -> _FailingDisconnectSession:
            self.create_kwargs = kwargs
            return _FailingDisconnectSession()

    client = _FailingDisconnectClient()
    set_client(cast(Any, client))

    pool = SessionPool()
    first_session = await pool.get_or_create("flaky-thread")

    # Should not raise even though the fake session's disconnect() always fails.
    await pool.disconnect("flaky-thread")

    second_session = await pool.get_or_create("flaky-thread")
    assert second_session is not first_session


@pytest.mark.asyncio
async def test_session_pool_turn_lock_is_stable_per_key_and_independent_of_pool_lock() -> None:
    """get_turn_lock() must return the same lock object for the same
    thread/isolation key (so callers actually serialize on it), a
    different lock for a different key, and must not be the same lock
    object used internally for pool bookkeeping (or disconnect() called
    while a turn lock is held would deadlock)."""
    pool = SessionPool()

    lock_a = pool.get_turn_lock("thread-a")
    lock_a_again = pool.get_turn_lock("thread-a")
    lock_b = pool.get_turn_lock("thread-b")

    assert lock_a is lock_a_again
    assert lock_a is not lock_b

    async with lock_a:
        # Must not deadlock: disconnect() only touches the pool's internal
        # bookkeeping lock, never the turn lock returned above.
        await asyncio.wait_for(pool.disconnect("thread-a"), timeout=1.0)


@pytest.mark.asyncio
async def test_foundry_session_pool_turn_lock_is_stable_per_key() -> None:
    """FoundrySessionPool must expose the same turn-lock guarantees as SessionPool."""
    pool = FoundrySessionPool()

    lock_a = pool.get_turn_lock("thread-a")
    lock_a_again = pool.get_turn_lock("thread-a")
    lock_b = pool.get_turn_lock("thread-b")

    assert lock_a is lock_a_again
    assert lock_a is not lock_b

    async with lock_a:
        await asyncio.wait_for(pool.disconnect("thread-a"), timeout=1.0)


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


@pytest.mark.asyncio
async def test_session_pool_isolates_same_thread_across_isolation_sessions() -> None:
    """Same thread_id in different isolation sessions must not share runtime state."""
    client = _FakeClient()
    set_client(cast(Any, client))

    pool = SessionPool()
    try:
        first = cast(
            _FakeSession, await pool.get_or_create("shared-thread", isolation_session_id="tenant-a")
        )
        second = cast(
            _FakeSession, await pool.get_or_create("shared-thread", isolation_session_id="tenant-b")
        )

        assert first is not second
    finally:
        await pool.shutdown()
