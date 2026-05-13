"""Tests for agent team platform endpoints (patterns + teams)."""

import pytest
from httpx import ASGITransport, AsyncClient

from agui_server import create_app
from src.patterns import PATTERNS, get_pattern

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------


def test_patterns_registry_has_five_entries() -> None:
    """All 5 patterns are registered."""
    assert len(PATTERNS) == 5
    expected = {
        "debate-critic",
        "generator-evaluator",
        "leadership",
        "planner-executor",
        "research-report",
    }
    assert set(PATTERNS.keys()) == expected


@pytest.mark.parametrize("pattern_id", list(PATTERNS.keys()))
def test_pattern_has_roles(pattern_id: str) -> None:
    """Every pattern has at least 2 roles."""
    pattern = get_pattern(pattern_id)
    assert pattern is not None
    assert len(pattern.roles) >= 2


def test_get_pattern_unknown_returns_none() -> None:
    assert get_pattern("nonexistent") is None


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_list_patterns_endpoint(app, monkeypatch) -> None:
    """GET /v1/patterns returns all 5 patterns."""
    monkeypatch.setattr("agui_server.CopilotClient", lambda: type("M", (), {
        "start": pytest.importorskip("unittest.mock").AsyncMock(),
        "stop": pytest.importorskip("unittest.mock").AsyncMock(),
    })())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/v1/patterns")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5
    ids = {p["id"] for p in data}
    assert "debate-critic" in ids
    assert "leadership" in ids
    for p in data:
        assert "name" in p
        assert "description" in p
        assert "roles" in p
        assert isinstance(p["roles"], list)


@pytest.mark.asyncio
async def test_teams_stream_unknown_pattern(app, monkeypatch) -> None:
    """POST /v1/teams/stream with unknown pattern returns 404."""
    monkeypatch.setattr("agui_server.CopilotClient", lambda: type("M", (), {
        "start": pytest.importorskip("unittest.mock").AsyncMock(),
        "stop": pytest.importorskip("unittest.mock").AsyncMock(),
    })())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/teams/stream",
            json={"pattern_id": "nonexistent", "prompt": "test"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_teams_stream_validation_max_rounds(app, monkeypatch) -> None:
    """POST /v1/teams/stream rejects max_rounds > 10."""
    monkeypatch.setattr("agui_server.CopilotClient", lambda: type("M", (), {
        "start": pytest.importorskip("unittest.mock").AsyncMock(),
        "stop": pytest.importorskip("unittest.mock").AsyncMock(),
    })())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/v1/teams/stream",
            json={"pattern_id": "debate-critic", "prompt": "test", "max_rounds": 99},
        )

    assert resp.status_code == 422
