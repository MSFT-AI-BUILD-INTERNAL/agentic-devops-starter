"""Tests for the Foundry / Azure Monitor observability setup."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _reset_observability_state() -> Generator[None, None, None]:
    """Reset the module-level _CONFIGURED flag between tests."""
    import observability

    observability._CONFIGURED = False
    yield
    observability._CONFIGURED = False


def test_disabled_when_connection_string_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without APPLICATIONINSIGHTS_CONNECTION_STRING, setup is a no-op."""
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)

    from observability import configure_observability

    assert configure_observability() is False


def test_enabled_when_connection_string_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the connection string set, Azure Monitor + agent instrumentation are configured."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.in.applicationinsights.azure.com/",
    )
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("ENABLE_SENSITIVE_DATA", raising=False)

    with (
        patch("azure.monitor.opentelemetry.configure_azure_monitor") as mock_cfg,
        patch("agent_framework.observability.enable_instrumentation") as mock_inst,
    ):
        from observability import configure_observability

        assert configure_observability() is True

    mock_cfg.assert_called_once()
    _, kwargs = mock_cfg.call_args
    assert kwargs["connection_string"].startswith("InstrumentationKey=")
    mock_inst.assert_called_once_with(enable_sensitive_data=False)

    import os

    assert os.environ["OTEL_SERVICE_NAME"] == "agentic-devops-starter"


def test_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """configure_observability() must only configure once even if called twice."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.in.applicationinsights.azure.com/",
    )

    with (
        patch("azure.monitor.opentelemetry.configure_azure_monitor") as mock_cfg,
        patch("agent_framework.observability.enable_instrumentation"),
    ):
        from observability import configure_observability

        assert configure_observability() is True
        assert configure_observability() is True

    assert mock_cfg.call_count == 1


def test_sensitive_data_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENABLE_SENSITIVE_DATA=true is forwarded to enable_instrumentation."""
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;"
        "IngestionEndpoint=https://example.in.applicationinsights.azure.com/",
    )
    monkeypatch.setenv("ENABLE_SENSITIVE_DATA", "true")

    with (
        patch("azure.monitor.opentelemetry.configure_azure_monitor"),
        patch("agent_framework.observability.enable_instrumentation") as mock_inst,
    ):
        from observability import configure_observability

        configure_observability()

    mock_inst.assert_called_once_with(enable_sensitive_data=True)
