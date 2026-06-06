"""Tests for session creation skill configuration."""

from __future__ import annotations

from typing import Any

import pytest

import src.skills as skills_module
import src.state as state_module
from src.state import SessionPool, set_client


class _FakeSession:
    async def disconnect(self) -> None:
        return None


class _FakeClient:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, Any] | None = None

    async def resume_session(self, *_args: Any, **_kwargs: Any) -> _FakeSession:
        raise RuntimeError("no saved session")

    async def create_session(self, **kwargs: Any) -> _FakeSession:
        self.create_kwargs = kwargs
        return _FakeSession()


@pytest.mark.asyncio
async def test_session_pool_enables_sdk_skills_when_directories_loaded() -> None:
    """The Copilot SDK must receive enable_skills=True with skill directories."""
    client = _FakeClient()
    set_client(client)  # type: ignore[arg-type]
    skills_module._skill_directories = ["/tmp/example-skills"]
    skills_module._loaded_skill_names = ["example"]

    try:
        pool = SessionPool()
        await pool.get_or_create("thread-with-skills")

        assert client.create_kwargs is not None
        assert client.create_kwargs["enable_skills"] is True
        assert client.create_kwargs["skill_directories"] == ["/tmp/example-skills"]
    finally:
        skills_module._skill_directories = []
        skills_module._loaded_skill_names = []
        state_module._client = None
