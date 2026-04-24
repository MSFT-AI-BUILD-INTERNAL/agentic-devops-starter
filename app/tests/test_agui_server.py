"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and agent integration.
Follows all constitution requirements including type safety and test coverage.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up environment variables, module-level constants, and mock Azure agent provisioning.

    agui_server reads ENDPOINT/DEPLOYMENT as module-level constants at import time,
    so we patch the attributes directly on the module.  _init_azure_agent is mocked
    so tests work without real Azure credentials.
    """
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "test-deployment")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AGUI_SERVER_URL", "http://127.0.0.1:5100/")
    import agui_server
    monkeypatch.setattr(agui_server, "ENDPOINT", "https://test.azure.com")
    monkeypatch.setattr(agui_server, "DEPLOYMENT", "test-deployment")
    monkeypatch.setattr(agui_server, "_init_azure_agent", AsyncMock(return_value="test-agent-id"))


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


@pytest.mark.asyncio
async def test_init_azure_agent_omits_temperature_top_p(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _init_azure_agent uses kwargs overload that omits temperature/top_p.

    The body-dict overload serializes None as JSON null; the Azure AI Agents service
    interprets null by storing server-side defaults (1.0) which o-series models reject.
    The kwargs overload filters out None values so temperature/top_p are absent from
    the request, preventing the service from storing any value for them.
    """
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", "https://test.azure.com")
    monkeypatch.setenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "test-deployment")
    import agui_server
    monkeypatch.setattr(agui_server, "ENDPOINT", "https://test.azure.com")
    monkeypatch.setattr(agui_server, "DEPLOYMENT", "test-deployment")

    agent = agui_server.create_agent()
    mock_response = AsyncMock()
    mock_response.id = "test-agent-id"
    mock_create = AsyncMock(return_value=mock_response)
    mock_client = AsyncMock()
    mock_client.create_agent = mock_create
    agent.chat_client.agents_client = mock_client

    await agui_server._init_azure_agent(agent)

    # Verify create_agent was called with kwargs (not body-dict overload)
    mock_create.assert_called_once()
    call_args = mock_create.call_args
    # kwargs overload: no positional args
    assert len(call_args.args) == 0, "Expected kwargs call, not body-dict positional arg"
    # temperature and top_p must NOT be in kwargs (SDK filters None → omitted from HTTP body)
    assert "temperature" not in call_args.kwargs, "temperature must not be passed"
    assert "top_p" not in call_args.kwargs, "top_p must not be passed"
    # Verify expected kwargs are present
    assert call_args.kwargs["model"] == "test-deployment"
    assert call_args.kwargs["name"] == "AGUIAssistant"
    assert "instructions" in call_args.kwargs
    assert agent.chat_client.agent_id == "test-agent-id"


def test_missing_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that appropriate error is raised when API keys are missing."""
    import agui_server

    # Patch module-level constants (load_dotenv reads .env at import time)
    monkeypatch.setattr(agui_server, "ENDPOINT", None)
    monkeypatch.setattr(agui_server, "DEPLOYMENT", None)

    with pytest.raises(ValueError, match="must be set"):
        agui_server.create_agent()
