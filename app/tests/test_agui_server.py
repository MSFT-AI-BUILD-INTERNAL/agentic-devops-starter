"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and configuration.
Follows all constitution requirements including type safety and test coverage.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from copilot import SubprocessConfig
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Create app with mocked CopilotClient so no real auth is needed."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
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


def test_lifespan_starts_client_with_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Startup must not pass GITHUB_TOKEN to the CopilotClient constructor."""
    import agui_server

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(agui_server.settings, "cli_otel_endpoint", "")
    monkeypatch.setattr(agui_server.settings, "cli_otel_file_path", "")
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    copilot_client = MagicMock(return_value=mock_client)
    monkeypatch.setattr(agui_server, "CopilotClient", copilot_client)

    with TestClient(agui_server.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    copilot_client.assert_called_once_with()


def test_lifespan_configures_copilot_cli_otel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Startup should pass CLI telemetry config when OTLP export is configured."""
    import agui_server

    monkeypatch.setattr(agui_server.settings, "cli_otel_endpoint", "http://otel:4318")
    monkeypatch.setattr(agui_server.settings, "cli_otel_exporter_type", "otlp-http")
    monkeypatch.setattr(agui_server.settings, "cli_otel_file_path", "")
    monkeypatch.setattr(agui_server.settings, "cli_otel_source_name", "test-service")
    monkeypatch.setattr(agui_server.settings, "cli_otel_capture_content", True)
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    copilot_client = MagicMock(return_value=mock_client)
    monkeypatch.setattr(agui_server, "CopilotClient", copilot_client)

    with TestClient(agui_server.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    copilot_client.assert_called_once()
    config = copilot_client.call_args.args[0]
    assert isinstance(config, SubprocessConfig)
    assert config.telemetry == {
        "exporter_type": "otlp-http",
        "source_name": "test-service",
        "capture_content": True,
        "otlp_endpoint": "http://otel:4318",
    }


def test_security_headers(client: TestClient) -> None:
    """Test that security headers are present in responses."""
    response = client.get("/health")
    assert response.status_code == 200

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_abort_thread_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The abort endpoint should call the session pool with the thread ID."""
    pool = MagicMock()
    pool.abort = AsyncMock(return_value=True)
    monkeypatch.setattr("src.api.routes.get_session_pool", lambda: pool)

    response = client.post("/v1/threads/thread-123/abort")

    assert response.status_code == 200
    assert response.json() == {"status": "aborted", "thread_id": "thread-123"}
    pool.abort.assert_awaited_once_with("thread-123")


def test_abort_thread_endpoint_reports_missing_thread(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The abort endpoint should report when no session is abortable."""
    pool = MagicMock()
    pool.abort = AsyncMock(return_value=False)
    monkeypatch.setattr("src.api.routes.get_session_pool", lambda: pool)

    response = client.post("/v1/threads/missing-thread/abort")

    assert response.status_code == 200
    assert response.json() == {"status": "not_found", "thread_id": "missing-thread"}
    pool.abort.assert_awaited_once_with("missing-thread")
