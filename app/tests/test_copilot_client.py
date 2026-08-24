"""Tests for direct GitHub Copilot API authentication."""

from src.thirdparty.copilot_client import CopilotClient, _credential_error_hint


def test_credential_hint_rejects_classic_pat() -> None:
    """Authentication errors explain that classic PATs are unsupported."""
    assert "Classic GitHub PATs are not supported" in _credential_error_hint("ghp_example")


def test_fine_grained_pat_uses_direct_developer_cli_authentication() -> None:
    """Fine-grained PATs authenticate directly with the developer CLI identity."""
    client = CopilotClient("github_pat_example")

    headers = client._copilot_headers()

    assert headers["authorization"] == "github_pat_example"
    assert headers["copilot-integration-id"] == "copilot-developer-cli"
    assert "editor-version" not in headers
