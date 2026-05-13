"""Tests for Fleet and Infinite Session endpoints.

Validates HTTP layer behavior: status codes, request validation, and job creation.
Background tasks (asyncio.create_task) don't execute during sync TestClient calls,
so jobs remain in 'pending' status — that's expected.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Create app with mocked CopilotClient so no real auth is needed."""
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    monkeypatch.setattr("agui_server.CopilotClient", lambda: mock_client)
    from agui_server import create_app

    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide a TestClient with lifespan handling."""
    return TestClient(app)


def test_fleet_endpoint_returns_202(client: TestClient) -> None:
    """POST /v1/fleet with valid body returns 202 and a job_id."""
    response = client.post(
        "/v1/fleet",
        json={"items": [{"prompt": "Hello"}]},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)


def test_fleet_endpoint_validation_empty_items(client: TestClient) -> None:
    """POST /v1/fleet with empty items list returns 422."""
    response = client.post("/v1/fleet", json={"items": []})
    assert response.status_code == 422


def test_fleet_endpoint_validation_too_many_items(client: TestClient) -> None:
    """POST /v1/fleet with 21 items returns 422."""
    items = [{"prompt": f"item {i}"} for i in range(21)]
    response = client.post("/v1/fleet", json={"items": items})
    assert response.status_code == 422


def test_infinite_session_endpoint_returns_202(client: TestClient) -> None:
    """POST /v1/infinite-session with valid body returns 202 and a job_id."""
    response = client.post(
        "/v1/infinite-session",
        json={"prompt": "Think deeply about this"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)


def test_infinite_session_validation_iterations_too_low(client: TestClient) -> None:
    """POST /v1/infinite-session with iterations=0 returns 422."""
    response = client.post(
        "/v1/infinite-session",
        json={"prompt": "test", "iterations": 0},
    )
    assert response.status_code == 422


def test_infinite_session_validation_iterations_too_high(client: TestClient) -> None:
    """POST /v1/infinite-session with iterations=11 returns 422."""
    response = client.post(
        "/v1/infinite-session",
        json={"prompt": "test", "iterations": 11},
    )
    assert response.status_code == 422


def test_job_status_not_found(client: TestClient) -> None:
    """GET /v1/jobs/nonexistent returns 404."""
    response = client.get("/v1/jobs/nonexistent-id")
    assert response.status_code == 404


def test_job_status_found(client: TestClient) -> None:
    """Create a job via fleet endpoint, then poll its status."""
    create_resp = client.post(
        "/v1/fleet",
        json={"items": [{"prompt": "test"}]},
    )
    job_id = create_resp.json()["job_id"]

    response = client.get(f"/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] in ("pending", "running", "completed", "failed")
