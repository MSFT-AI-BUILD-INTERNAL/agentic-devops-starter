"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and agent integration.
Follows all constitution requirements including type safety and test coverage.
"""

import json
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up test environment variables."""
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "test-deployment")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AGUI_SERVER_URL", "http://127.0.0.1:5100/")


def test_server_creation(test_env: None) -> None:
    """Test that the FastAPI app can be created."""
    from agui_server import create_app

    app = create_app()
    assert app is not None
    assert app.title == "Agentic DevOps Starter AG-UI Server"


def test_server_has_docs(test_env: None) -> None:
    """Test that OpenAPI docs are available."""
    from agui_server import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/docs")
    assert response.status_code == 200


def test_health_check_endpoint(test_env: None) -> None:
    """Test that the health check endpoint is available."""
    from agui_server import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_security_headers(test_env: None) -> None:
    """Test that security headers are present in responses."""
    from agui_server import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200

    # Verify security headers are present
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_get_time_zone_tool() -> None:
    """Test the get_time_zone server-side tool."""
    from agui_server import get_time_zone

    # Test known locations
    assert "Pacific Time" in get_time_zone("Seattle")
    assert "Pacific Time" in get_time_zone("San Francisco")
    assert "Eastern Time" in get_time_zone("New York")
    assert "Greenwich Mean Time" in get_time_zone("London")

    # Test case insensitivity
    assert "Pacific Time" in get_time_zone("SEATTLE")
    assert "Pacific Time" in get_time_zone("seattle")

    # Test unknown location
    result = get_time_zone("Unknown City")
    assert "not available" in result


def test_agent_creation(test_env: None) -> None:
    """Test that the agent can be created with proper configuration."""
    from agui_server import create_agent

    agent = create_agent()
    assert agent is not None
    assert agent.name == "AGUIAssistant"


def test_missing_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that appropriate error is raised when API keys are missing."""
    import agui_server

    # Patch module-level constants (load_dotenv reads .env at import time)
    monkeypatch.setattr(agui_server, "ENDPOINT", None)
    monkeypatch.setattr(agui_server, "DEPLOYMENT", None)

    with pytest.raises(ValueError, match="must be set"):
        agui_server.create_agent()


def test_agent_endpoint_emits_run_error_and_run_finished_on_agent_failure(
    test_env: None,
) -> None:
    """Agent endpoint must emit RUN_ERROR + RUN_FINISHED when run_agent raises.

    This validates the root-cause fix: before this fix, an unhandled exception
    inside the streaming generator terminated the SSE stream without sending
    RUN_FINISHED, causing the client to report 'Stream ended without
    RUN_FINISHED event'.
    """
    from agui_server import create_app

    app = create_app()
    client = TestClient(app)

    async def _failing_run_agent(_input: dict) -> AsyncGenerator:  # type: ignore[type-arg]
        """Async generator that immediately raises to simulate a backend failure."""
        raise RuntimeError("Simulated Azure AI failure")
        yield  # pragma: no cover – makes this an async generator

    with patch(
        "agui_server.AgentFrameworkAgent.run_agent",
        new=_failing_run_agent,
    ):
        response = client.post(
            "/",
            json={"messages": [{"role": "user", "content": "hello"}], "thread_id": "test-thread"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Collect all SSE event types from the stream
    event_types = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            data = line[6:]
            event = json.loads(data)
            event_types.append(event.get("type"))

    assert "RUN_ERROR" in event_types, "RUN_ERROR must be emitted when agent fails"
    assert "RUN_FINISHED" in event_types, "RUN_FINISHED must always terminate the stream"
    # RUN_ERROR must precede RUN_FINISHED
    assert event_types.index("RUN_ERROR") < event_types.index("RUN_FINISHED")
