"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and agent integration.
Follows all constitution requirements including type safety and test coverage.
"""

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

    # @ai_function wraps sync tools; the return value is always str at runtime.
    for location, expected in [
        ("Seattle", "Pacific Time"),
        ("San Francisco", "Pacific Time"),
        ("New York", "Eastern Time"),
        ("London", "Greenwich Mean Time"),
        ("SEATTLE", "Pacific Time"),
        ("seattle", "Pacific Time"),
    ]:
        result = get_time_zone(location)
        assert isinstance(result, str), f"get_time_zone({location!r}) did not return str"
        assert expected in result, f"Expected {expected!r} in get_time_zone({location!r}), got {result!r}"

    # Test unknown location
    result = get_time_zone("Unknown City")
    assert isinstance(result, str)
    assert "not available" in result


def test_agent_creation(test_env: None) -> None:
    """Test that the agent can be created with proper configuration."""
    from agui_server import create_agent

    agent = create_agent()
    assert agent is not None
    assert agent.name == "AGUIAssistant"


def test_agent_uses_compatible_client(test_env: None) -> None:
    """Test that the agent uses the compatible client that strips unsupported params."""
    from agui_server import _CompatibleAzureAIAgentClient, create_agent

    agent = create_agent()
    assert isinstance(agent.chat_client, _CompatibleAzureAIAgentClient), (
        "Agent must use _CompatibleAzureAIAgentClient to avoid 'top_p' errors on o-series models"
    )


def test_compatible_client_removes_top_p(test_env: None) -> None:
    """Test that _CompatibleAzureAIAgentClient removes top_p and temperature from run options."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch

    from agent_framework.azure import AzureAIAgentClient

    from agui_server import _CompatibleAzureAIAgentClient

    test_deployment = "test-deployment"
    test_top_p = 1.0
    test_temperature = 0.7

    client = _CompatibleAzureAIAgentClient(
        project_endpoint="https://test.azure.com",
        model_deployment_name=test_deployment,
        credential=MagicMock(),
    )

    # Simulate super()._prepare_options returning run_options with top_p and temperature
    run_options_with_params = {
        "model": test_deployment,
        "top_p": test_top_p,
        "temperature": test_temperature,
        "tools": [],
    }
    mock_super_result = (run_options_with_params, None)

    async def run_test() -> tuple[dict[str, object], object]:
        with patch.object(
            AzureAIAgentClient,
            "_prepare_options",
            new=AsyncMock(return_value=mock_super_result),
        ):
            return await client._prepare_options([], MagicMock())

    result_options, result_actions = asyncio.run(run_test())

    assert "top_p" not in result_options, "top_p must be removed from run options"
    assert "temperature" not in result_options, "temperature must be removed from run options"
    assert result_options.get("model") == test_deployment, "other options must be preserved"
    assert result_actions is None


def test_missing_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that appropriate error is raised when API keys are missing."""
    import agui_server

    # Patch module-level constants (load_dotenv reads .env at import time)
    monkeypatch.setattr(agui_server, "ENDPOINT", None)
    monkeypatch.setattr(agui_server, "DEPLOYMENT", None)

    with pytest.raises(ValueError, match="must be set"):
        agui_server.create_agent()
