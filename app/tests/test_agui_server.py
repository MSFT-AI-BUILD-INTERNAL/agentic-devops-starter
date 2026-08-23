"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and configuration.
Follows all constitution requirements including type safety and test coverage.
"""

from unittest.mock import ANY, AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

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
    monkeypatch.setattr("agui_server.CopilotClient", lambda *args, **kwargs: mock_client)
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


def test_lifespan_starts_client_without_permanent_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Startup must not pass a permanent GitHub token to the CopilotClient constructor."""
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
    copilot_client.assert_called_once_with(on_list_models=ANY)


def test_github_oauth_login_redirects_with_csrf_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """OAuth login should redirect to GitHub with the configured callback and state."""
    import agui_server

    monkeypatch.setattr(agui_server.settings, "github_client_id", "client-id")
    monkeypatch.setattr(agui_server.settings, "github_client_secret", "client-secret")
    monkeypatch.setattr(
        agui_server.settings,
        "github_oauth_redirect_uri",
        "https://app-agentic-devops.azurewebsites.net/auth/callback",
    )

    with TestClient(agui_server.create_app()) as test_client:
        response = test_client.get("/auth/login", follow_redirects=False)

    assert response.status_code == 307
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == [agui_server.settings.github_oauth_redirect_uri]
    assert len(query["state"][0]) >= 32
    assert "set-cookie" not in response.headers


def test_github_oauth_callback_stores_token_in_secure_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth callback must keep the GitHub token server-side."""
    import agui_server
    from src.api import auth

    monkeypatch.setattr(agui_server.settings, "github_client_id", "client-id")
    monkeypatch.setattr(agui_server.settings, "github_client_secret", "client-secret")
    monkeypatch.setattr(
        agui_server.settings,
        "github_oauth_redirect_uri",
        "https://app-agentic-devops.azurewebsites.net/auth/callback",
    )
    monkeypatch.setattr(
        "src.api.routes.exchange_code",
        AsyncMock(return_value=auth.OAuthToken(access_token="user-token")),
    )

    with TestClient(agui_server.create_app()) as test_client:
        login = test_client.get(
            "/auth/login",
            headers={"user-agent": "same-browser"},
            follow_redirects=False,
        )
        state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
        response = test_client.get(
            f"/auth/callback?code=authorization-code&state={state}",
            headers={"user-agent": "same-browser"},
            follow_redirects=False,
        )

    assert response.status_code == 307
    cookie = response.headers["set-cookie"]
    assert "github_oauth_session=" in cookie
    assert "user-token" not in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie


def test_github_oauth_callback_rejects_mismatched_state_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth callback should reject requests from a different browser context."""
    import agui_server
    from src.api import auth

    monkeypatch.setattr(agui_server.settings, "github_client_id", "client-id")
    monkeypatch.setattr(agui_server.settings, "github_client_secret", "client-secret")
    monkeypatch.setattr(
        agui_server.settings,
        "github_oauth_redirect_uri",
        "https://app-agentic-devops.azurewebsites.net/auth/callback",
    )
    monkeypatch.setattr(
        "src.api.routes.exchange_code",
        AsyncMock(return_value=auth.OAuthToken(access_token="user-token")),
    )

    with TestClient(agui_server.create_app()) as test_client:
        login = test_client.get(
            "/auth/login",
            headers={"user-agent": "same-browser"},
            follow_redirects=False,
        )
        state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
        response = test_client.get(
            f"/auth/callback?code=authorization-code&state={state}",
            headers={"user-agent": "different-browser"},
            follow_redirects=False,
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_github_oauth_exchange_code_posts_configured_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth token exchange should use the same GitHub App callback URI."""
    from src.api import auth

    captured_payload: dict[str, str] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, str]:
            return {"access_token": "user-token"}

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 10.0

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(
            self,
            url: str,
            headers: dict[str, str],
            json: dict[str, str],
        ) -> FakeResponse:
            assert url == "https://github.com/login/oauth/access_token"
            assert headers == {"Accept": "application/json"}
            captured_payload.update(json)
            return FakeResponse()

    monkeypatch.setattr(auth.settings, "github_client_id", "client-id")
    monkeypatch.setattr(auth.settings, "github_client_secret", "client-secret")
    monkeypatch.setattr(
        auth.settings,
        "github_oauth_redirect_uri",
        "https://app-agentic-devops.azurewebsites.net/auth/callback",
    )
    monkeypatch.setattr(auth.httpx, "AsyncClient", FakeAsyncClient)

    token = await auth.exchange_code("authorization-code")

    assert token.access_token == "user-token"
    assert captured_payload == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "code": "authorization-code",
        "redirect_uri": "https://app-agentic-devops.azurewebsites.net/auth/callback",
    }


def test_github_oauth_session_rejects_anonymous_browser(client: TestClient) -> None:
    """The authenticated-session endpoint must reject requests without a session cookie."""
    response = client.get("/auth/session")

    assert response.status_code == 401


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
    pool.abort.assert_awaited_once_with("thread-123", isolation_session_id="thread-123")


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
    pool.abort.assert_awaited_once_with("missing-thread", isolation_session_id="missing-thread")


def test_abort_thread_endpoint_uses_isolation_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Abort should scope by the caller isolation session header."""
    pool = MagicMock()
    pool.abort = AsyncMock(return_value=True)
    monkeypatch.setattr("src.api.routes.get_session_pool", lambda: pool)

    response = client.post(
        "/v1/threads/thread-123/abort",
        headers={"X-Isolation-Session-ID": "tenant-a"},
    )

    assert response.status_code == 200
    pool.abort.assert_awaited_once_with("thread-123", isolation_session_id="tenant-a")


def test_anthropic_models_requires_thirdparty_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Third-party model listing should reject unauthenticated callers."""
    monkeypatch.setattr("src.api.routes.settings.thirdparty_api_key", "")

    response = client.get("/v1/models")

    assert response.status_code == 503
    assert response.json() == {"detail": "THIRDPARTY_API_KEY is not configured"}


def test_anthropic_models_rejects_wrong_thirdparty_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Third-party model listing should reject invalid caller API keys."""
    monkeypatch.setattr("src.api.routes.settings.thirdparty_api_key", "client-key")

    response = client.get("/v1/models", headers={"x-api-key": "wrong-key"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Third-party API authentication required"}


def test_anthropic_messages_requires_thirdparty_pat(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Third-party messages should fail fast when the server PAT is missing."""
    monkeypatch.setattr("src.api.routes.settings.thirdparty_api_key", "client-key")
    monkeypatch.setattr("src.api.routes.settings.thirdparty_github_pat", "")
    pool = MagicMock()
    pool.get_or_create = AsyncMock()
    monkeypatch.setattr("src.api.routes.get_session_pool", lambda: pool)

    response = client.post(
        "/v1/messages",
        headers={"x-api-key": "client-key", "X-Isolation-Session-ID": "tenant-a"},
        json={"model": "gpt-4.1", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "THIRDPARTY_GITHUB_PAT is not configured"}
    pool.get_or_create.assert_not_called()


def test_anthropic_messages_requires_isolation_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Third-party messages should not fall back to a shared isolation namespace."""
    monkeypatch.setattr("src.api.routes.settings.thirdparty_api_key", "client-key")
    monkeypatch.setattr("src.api.routes.settings.thirdparty_github_pat", "server-token")
    pool = MagicMock()
    pool.get_or_create = AsyncMock()
    monkeypatch.setattr("src.api.routes.get_session_pool", lambda: pool)

    response = client.post(
        "/v1/messages",
        headers={"x-api-key": "client-key"},
        json={"model": "gpt-4.1", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "X-Isolation-Session-ID header is required"}
    pool.get_or_create.assert_not_called()


def test_anthropic_messages_uses_required_isolation_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Third-party messages should pass the caller isolation namespace to the session pool."""
    monkeypatch.setattr("src.api.routes.settings.thirdparty_api_key", "client-key")
    monkeypatch.setattr("src.api.routes.settings.thirdparty_github_pat", "server-token")
    pool = MagicMock()
    pool.get_or_create = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("src.api.routes.get_session_pool", lambda: pool)

    response = client.post(
        "/v1/messages",
        headers={"x-api-key": "client-key", "X-Isolation-Session-ID": "tenant-a"},
        json={"model": "gpt-4.1", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Session initialization failed: boom"}
    pool.get_or_create.assert_awaited_once_with(
        "anthropic-v1", "server-token", isolation_session_id="tenant-a"
    )
