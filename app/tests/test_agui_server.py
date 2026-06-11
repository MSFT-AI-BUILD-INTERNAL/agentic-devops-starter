"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and configuration.
Follows all constitution requirements including type safety and test coverage.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from copilot.generated.session_events import (
    AssistantMessageDeltaData,
    SessionEvent,
    SessionEventType,
    SessionIdleData,
)
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
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    copilot_client = MagicMock(return_value=mock_client)
    monkeypatch.setattr("agui_server.CopilotClient", copilot_client)
    from agui_server import create_app

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    copilot_client.assert_called_once_with()


def test_security_headers(client: TestClient) -> None:
    """Test that security headers are present in responses."""
    response = client.get("/health")
    assert response.status_code == 200

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class _FakeSession:
    """Minimal Copilot session double that emits one text delta and idle."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.sent_prompts: list[str] = []
        self._handler: Callable[[SessionEvent], None] | None = None

    def on(self, handler: Callable[[SessionEvent], None]) -> Callable[[], None]:
        self._handler = handler

        def unsubscribe() -> None:
            self._handler = None

        return unsubscribe

    async def send(self, prompt: str) -> None:
        self.sent_prompts.append(prompt)
        self._emit(
            AssistantMessageDeltaData(delta_content=self.response_text, message_id=uuid4().hex),
            SessionEventType.ASSISTANT_MESSAGE_DELTA,
        )
        self._emit(SessionIdleData(), SessionEventType.SESSION_IDLE)

    async def disconnect(self) -> None:
        return None

    def _emit(self, data: Any, event_type: SessionEventType) -> None:
        if self._handler is None:
            return
        self._handler(
            SessionEvent(
                data=data,
                id=uuid4(),
                timestamp=datetime.now(UTC),
                type=event_type,
            )
        )


class _FleetChatClient:
    """CopilotClient double that records persistent and branch sessions."""

    def __init__(self) -> None:
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.created_sessions: list[_FakeSession] = []

    async def resume_session(self, *_args: Any, **_kwargs: Any) -> _FakeSession:
        raise RuntimeError("missing persisted session")

    async def create_session(self, **kwargs: Any) -> _FakeSession:
        is_persistent_chat = "session_id" in kwargs
        session = _FakeSession("final answer" if is_persistent_chat else "fleet finding")
        self.created_sessions.append(session)
        return session


def test_general_chat_uses_fleet_before_streaming_final_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """General chat should run parallel branch sessions before the final session send."""
    fake_client = _FleetChatClient()
    monkeypatch.setattr("agui_server.CopilotClient", lambda: fake_client)
    from agui_server import create_app

    with TestClient(create_app()) as client:
        response = client.post(
            "/",
            json={
                "thread_id": "fleet-chat-thread",
                "messages": [{"role": "user", "content": "Compare two deployment options"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    assert "final answer" in response.text
    assert len(fake_client.created_sessions) == 4
    persistent_session = fake_client.created_sessions[0]
    branch_sessions = fake_client.created_sessions[1:]
    assert all(session.sent_prompts for session in branch_sessions)
    assert "parallel fleet analyses" in persistent_session.sent_prompts[0]
    assert "Original user request:\nCompare two deployment options" in persistent_session.sent_prompts[0]
