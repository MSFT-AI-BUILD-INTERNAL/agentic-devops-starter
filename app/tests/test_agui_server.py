"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and configuration.
Follows all constitution requirements including type safety and test coverage.
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
    monkeypatch.setattr("agui_server.CopilotClient", lambda *_args, **_kwargs: mock_client)
    from agui_server import create_app

    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide a TestClient with lifespan handling."""
    return TestClient(app)


def test_server_creation(app: FastAPI) -> None:
    """Test that the FastAPI app can be created."""
    assert app is not None
    assert app.title == "Agentic DevOps Starter AG-UI Server"


def test_server_has_docs(client: TestClient) -> None:
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_health_check_endpoint(client: TestClient) -> None:
    """Test that the health check endpoint is available."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_security_headers(client: TestClient) -> None:
    """Test that security headers are present in responses."""
    response = client.get("/health")
    assert response.status_code == 200

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
