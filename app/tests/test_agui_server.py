"""Tests for the AG-UI server.

Tests the AG-UI server endpoints and configuration.
Follows all constitution requirements including type safety and test coverage.
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.storage import BlobStorageClient, UploadedBlob


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


def test_file_upload_returns_503_when_storage_not_configured(client: TestClient) -> None:
    """Without Azure Storage env vars the upload endpoint must fail closed.

    The default test fixture doesn't set AZURE_STORAGE_BLOB_ENDPOINT, so the
    backend reports storage is unavailable rather than silently no-oping.
    """
    response = client.post(
        "/v1/files/upload",
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 503
    assert "storage" in response.json()["detail"].lower()


def test_file_upload_streams_copilot_response_via_blob(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The endpoint must (a) upload to blob, (b) download, (c) forward to Copilot.

    The whole flow is mocked: a fake BlobStorageClient records the bytes
    received from the request and returns deterministic content from
    ``download_text``. The Copilot session is also mocked so we can assert
    that the prompt passed to it contains the file's contents — i.e. the
    file really was round-tripped through blob storage.
    """
    captured: dict[str, object] = {}

    class FakeBlob(BlobStorageClient):
        def __init__(self) -> None:
            self._account_url = "https://fake/"
            self._container_name = "uploads"

        async def upload(  # type: ignore[override]
            self, stream: object, original_filename: str, content_type: str | None
        ) -> UploadedBlob:
            data = stream.read() if hasattr(stream, "read") else b""
            captured["uploaded_bytes"] = data
            captured["filename"] = original_filename
            captured["content_type"] = content_type
            return UploadedBlob(
                name=f"abc-{original_filename}",
                container=self._container_name,
                size=len(data),
                content_type=content_type,
            )

        async def download_text(self, blob_name: str) -> str:  # type: ignore[override]
            captured["downloaded_blob"] = blob_name
            return "ROUND_TRIPPED_FILE_BODY"

        async def close(self) -> None:
            return None

    # Patch storage construction so the lifespan installs our fake client.
    fake_blob = FakeBlob()

    # Patch the CopilotClient and storage factory before importing create_app.
    mock_copilot = MagicMock()
    mock_copilot.start = AsyncMock()
    mock_copilot.stop = AsyncMock()
    monkeypatch.setattr(
        "agui_server.CopilotClient", lambda *_a, **_kw: mock_copilot
    )
    monkeypatch.setattr("agui_server._build_storage_client", lambda: fake_blob)

    # Patch the Copilot session pool so the SSE generator runs end-to-end
    # without contacting GitHub Copilot. The fake send() invokes the
    # subscribed handler with a SessionIdleData so the generator terminates.
    sent_prompts: list[str] = []

    from copilot.generated.session_events import SessionIdleData

    class _IdleEvent:
        """Minimal duck-typed stand-in for ``SessionEvent``.

        ``_stream_copilot_prompt`` only accesses ``event.data`` via
        ``match`` against the concrete payload classes, so providing a real
        ``SessionIdleData`` payload is enough to trigger the idle branch.
        """

        def __init__(self) -> None:
            self.data: object = SessionIdleData()

    from src import routes as routes_mod

    class FakeSession:
        def __init__(self) -> None:
            self._handler: object = None

        def on(self, handler: object) -> object:
            self._handler = handler
            return lambda: None

        async def send(self, prompt: str) -> None:
            sent_prompts.append(prompt)
            if self._handler is not None and callable(self._handler):
                # Emit an idle event so _stream_copilot_prompt exits cleanly.
                self._handler(_IdleEvent())

    class FakeSessionPool:
        def __init__(self, session: FakeSession) -> None:
            self._session = session

        async def get_or_create(self, _thread_id: str) -> FakeSession:
            return self._session

        async def disconnect(self, _thread_id: str) -> None:
            return None

    fake_pool = FakeSessionPool(FakeSession())
    monkeypatch.setattr(routes_mod, "get_session_pool", lambda: fake_pool)

    from agui_server import create_app

    with TestClient(create_app()) as test_client:
        response = test_client.post(
            "/v1/files/upload",
            files={"file": ("notes.txt", BytesIO(b"line1\nline2\n"), "text/plain")},
            data={"thread_id": "t-1", "prompt": "summarize"},
        )

    assert response.status_code == 200
    body = response.text
    assert "RUN_STARTED" in body
    assert "RUN_FINISHED" in body

    # The file's bytes were uploaded to blob storage.
    assert captured["uploaded_bytes"] == b"line1\nline2\n"
    assert captured["filename"] == "notes.txt"
    assert captured["content_type"] == "text/plain"
    # The blob was downloaded back before forwarding to Copilot.
    assert captured["downloaded_blob"] == "abc-notes.txt"
    # The Copilot session received a prompt containing the downloaded text.
    assert any("ROUND_TRIPPED_FILE_BODY" in p for p in sent_prompts)
    assert any("summarize" in p for p in sent_prompts)

