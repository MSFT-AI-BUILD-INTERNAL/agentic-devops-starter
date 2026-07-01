"""Tests for use-case-oriented backend source modules."""

import pytest

from src.api.models import FleetItem, FleetRequest
from src.api.routes import initialization_error_message
from src.core.config import Settings
from src.runtime.jobs import create_job
from src.storage.file_validation import validate_file_size
from src.teams.patterns import PATTERNS


def test_use_case_packages_expose_backend_modules() -> None:
    """Core backend use cases should be importable by package."""
    assert Settings().port == 5100
    assert FleetRequest(items=[FleetItem(prompt="hello")]).items[0].prompt == "hello"
    assert callable(create_job)
    try:
        validate_file_size(1)
    except ValueError as exc:
        pytest.fail(f"Expected one-byte files to be valid: {exc}")
    assert "debate-critic" in PATTERNS


def test_legacy_module_imports_remain_available() -> None:
    """Existing imports should continue to resolve during migration."""
    from src.config import settings
    from src.models import FleetRequest as LegacyFleetRequest
    from src.patterns import PATTERNS as LEGACY_PATTERNS

    assert settings.port == 5100
    assert LegacyFleetRequest is FleetRequest
    assert LEGACY_PATTERNS is PATTERNS


@pytest.mark.parametrize(
    "raw_error",
    [
        "Foundry BYOK is not configured: missing FOUNDRY_API_KEY",
        "Foundry BYOK is not configured: FOUNDRY_WIRE_API must be responses or completions",
        "Foundry BYOK is not configured: Azure Identity authentication failed",
    ],
)
def test_foundry_initialization_errors_are_client_safe(raw_error: str) -> None:
    """Known Foundry setup errors should not echo raw exception text to clients."""
    message = initialization_error_message(RuntimeError(raw_error), "default")

    assert message == "Foundry BYOK is not configured. Check the server's Azure AI Foundry settings."
    assert raw_error not in message


def test_non_foundry_initialization_errors_use_default_message() -> None:
    """Unexpected initialization errors should use the provided safe default."""
    assert initialization_error_message(RuntimeError("database password failed"), "default") == "default"
