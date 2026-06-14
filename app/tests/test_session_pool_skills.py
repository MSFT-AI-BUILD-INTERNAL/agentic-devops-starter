"""Tests for session creation skill configuration."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast

import pytest

import src.skills as skills_module
import src.state as state_module
from src.skills import load_skills
from src.state import SessionPool, set_client


class _FakeSession:
    def __init__(self) -> None:
        self.abort_count = 0

    async def abort(self) -> None:
        self.abort_count += 1

    async def disconnect(self) -> None:
        pass


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
        session = await pool.get_or_create("thread-to-abort")

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
