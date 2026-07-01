"""Tests for the Azure Monitor observability setup."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from src.core import observability
from src.core.observability import configure_observability


@pytest.fixture(autouse=True)
def _reset_observability_state() -> Generator[None, None, None]:
    """Reset the module-level _CONFIGURED flag between tests."""
    observability._CONFIGURED = False
    yield
    observability._CONFIGURED = False


def test_disabled_when_connection_string_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without APPLICATIONINSIGHTS_CONNECTION_STRING, setup is a no-op."""
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)

    assert configure_observability() is False


def test_enabled_when_connection_string_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the connection string set, Azure Monitor is configured."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.in.applicationinsights.azure.com/",
    )
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as mock_cfg:
        assert configure_observability() is True

    mock_cfg.assert_called_once()
    _, kwargs = mock_cfg.call_args
    assert kwargs["connection_string"].startswith("InstrumentationKey=")

    import os

    assert os.environ["OTEL_SERVICE_NAME"] == "agentic-devops-starter"


def test_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """configure_observability() must only configure once even if called twice."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.in.applicationinsights.azure.com/",
    )

    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as mock_cfg:
        assert configure_observability() is True
        assert configure_observability() is True

    assert mock_cfg.call_count == 1


def test_repeated_calls_after_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """After initial configuration, subsequent calls return True without reconfiguring."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.in.applicationinsights.azure.com/",
    )

    with patch("azure.monitor.opentelemetry.configure_azure_monitor"):
        configure_observability()

    # Second call without patch — should return True from _CONFIGURED guard
    assert configure_observability() is True
