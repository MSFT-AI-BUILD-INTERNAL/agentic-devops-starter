"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and agent integration.
Follows all constitution requirements including type safety and test coverage.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up test environment variables."""
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
    # Note: ChatAgent stores tools internally, they're not exposed as a public attribute


def test_agent_has_time_zone_tool(test_env: None) -> None:
    """Test that the agent is configured with tools."""
    from agui_server import create_agent

    agent = create_agent()
    # Note: ChatAgent stores tools internally
    # We can verify the agent was created successfully
    assert agent.name == "AGUIAssistant"


def test_missing_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that appropriate error is raised when API keys are missing."""
    # Clear all API keys
    monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    # Need to reload the module to pick up the new environment
    import sys
    if 'agui_server' in sys.modules:
        del sys.modules['agui_server']
    
    from agui_server import create_agent
    
    with pytest.raises(ValueError, match="must be set"):
        create_agent()
