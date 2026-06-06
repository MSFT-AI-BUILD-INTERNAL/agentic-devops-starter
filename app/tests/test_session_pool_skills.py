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
def reset_skills_and_client(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    monkeypatch.setattr(skills_module, "_skill_directories", [])
    monkeypatch.setattr(skills_module, "_loaded_skill_names", [])
    monkeypatch.setattr(state_module, "_client", None)
    yield


@pytest.mark.asyncio
async def test_session_pool_enables_sdk_skills_when_directories_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Copilot SDK must receive enable_skills=True with skill directories."""
    client = _FakeClient()
    monkeypatch.delenv("COPILOT_API_SKILL_DIRECTORIES", raising=False)
    skill_directories = load_skills()
    set_client(cast(Any, client))

    pool = SessionPool()
    await pool.get_or_create("thread-with-skills")

    assert client.create_kwargs is not None
    assert client.create_kwargs["enable_skills"] is True
    assert client.create_kwargs["skill_directories"] == skill_directories
