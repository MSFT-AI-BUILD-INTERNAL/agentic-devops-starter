"""Tests for use-case focused application modules."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.use_cases.background_jobs import get_job_status
from src.use_cases.teams import list_team_patterns
from src.use_cases.threads import abort_thread_session, delete_thread_sessions


@pytest.mark.asyncio
async def test_delete_thread_sessions_disconnects_all_pools() -> None:
    """Deleting a thread should clean up standard and Foundry sessions."""
    pool = MagicMock()
    pool.disconnect = AsyncMock()
    foundry_pool = MagicMock()
    foundry_pool.disconnect = AsyncMock()

    result = await delete_thread_sessions("thread-123", pool, foundry_pool)

    assert result == {"status": "deleted", "thread_id": "thread-123"}
    pool.disconnect.assert_awaited_once_with("thread-123")
    foundry_pool.disconnect.assert_awaited_once_with("thread-123")


@pytest.mark.asyncio
async def test_abort_thread_session_reports_pool_result() -> None:
    """Aborting a thread should expose whether the pool found an active session."""
    pool = MagicMock()
    pool.abort = AsyncMock(return_value=False)

    result = await abort_thread_session("missing-thread", pool)

    assert result == {"status": "not_found", "thread_id": "missing-thread"}
    pool.abort.assert_awaited_once_with("missing-thread")


@pytest.mark.asyncio
async def test_get_job_status_unknown_raises_404() -> None:
    """Unknown jobs should still surface as HTTP 404 from the job use case."""
    with pytest.raises(HTTPException) as exc_info:
        await get_job_status("does-not-exist")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Job not found"


@pytest.mark.asyncio
async def test_list_team_patterns_returns_registered_summaries() -> None:
    """The team-pattern use case should expose registered pattern summaries."""
    patterns = await list_team_patterns()

    assert len(patterns) == 5
    assert {pattern.id for pattern in patterns} >= {"debate-critic", "leadership"}
    assert all(pattern.roles for pattern in patterns)
