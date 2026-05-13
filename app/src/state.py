"""Shared application state for the CopilotClient instance."""

from copilot import CopilotClient

_client: CopilotClient | None = None


def set_client(client: CopilotClient) -> None:
    """Store the shared CopilotClient instance."""
    global _client
    _client = client


def get_client() -> CopilotClient:
    """Retrieve the shared CopilotClient instance."""
    if _client is None:
        raise RuntimeError("CopilotClient not initialized")
    return _client
