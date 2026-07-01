"""Tests for use-case-oriented backend source modules."""

from src.api.models import FleetItem, FleetRequest
from src.core.config import Settings
from src.runtime.jobs import create_job
from src.storage.file_validation import validate_file_size
from src.teams.patterns import PATTERNS


def test_use_case_packages_expose_backend_modules() -> None:
    """Core backend use cases should be importable by package."""
    assert Settings().port == 5100
    assert FleetRequest(items=[FleetItem(prompt="hello")]).items[0].prompt == "hello"
    assert callable(create_job)
    validate_file_size(1)
    assert "debate-critic" in PATTERNS


def test_legacy_module_imports_remain_available() -> None:
    """Existing imports should continue to resolve during migration."""
    from src.config import settings
    from src.models import FleetRequest as LegacyFleetRequest
    from src.patterns import PATTERNS as LEGACY_PATTERNS

    assert settings.port == 5100
    assert LegacyFleetRequest is FleetRequest
    assert LEGACY_PATTERNS is PATTERNS
