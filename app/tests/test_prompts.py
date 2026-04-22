"""Tests for PromptManager."""

from pathlib import Path

import pytest

from src.prompts.prompt_manager import PromptManager


@pytest.fixture
def default_manager() -> PromptManager:
    """Return a PromptManager loaded from the default system_prompts.yaml."""
    return PromptManager()


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def test_loads_default_yaml(default_manager: PromptManager) -> None:
    """PromptManager must successfully load the bundled YAML file."""
    assert len(default_manager._prompts) > 0


def test_loads_from_custom_path(tmp_path: Path) -> None:
    """PromptManager must load prompts from a custom path."""
    yaml_file = tmp_path / "prompts.yaml"
    yaml_file.write_text(
        "prompts:\n  test.system: |\n    You are a test agent.\n",
        encoding="utf-8",
    )
    manager = PromptManager(prompts_path=yaml_file)
    assert manager.get("test.system") == "You are a test agent."


def test_handles_missing_file() -> None:
    """PromptManager must not raise if the prompts file is missing."""
    manager = PromptManager(prompts_path=Path("/nonexistent/path.yaml"))
    # Should fall back to built-in default
    assert isinstance(manager.get("anything.system"), str)
    assert len(manager.get("anything.system")) > 0


def test_handles_invalid_yaml_structure(tmp_path: Path) -> None:
    """PromptManager must not raise for YAML without a 'prompts' key."""
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text("key: value\n", encoding="utf-8")
    manager = PromptManager(prompts_path=yaml_file)
    # Should fall back gracefully
    assert isinstance(manager.get("anything.system"), str)


# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------


def test_resolves_existing_key(default_manager: PromptManager) -> None:
    """Resolves a key that exists in the YAML."""
    prompt = default_manager.get("default.system")
    assert isinstance(prompt, str)
    assert len(prompt.strip()) > 0


def test_resolves_agent_specific_key(default_manager: PromptManager) -> None:
    """Resolves an agent-specific key like 'aguiassistant.system'."""
    prompt = default_manager.get("aguiassistant.system")
    assert isinstance(prompt, str)
    assert len(prompt.strip()) > 0


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------


def test_falls_back_to_default_system(default_manager: PromptManager) -> None:
    """Missing keys must fall back to 'default.system'."""
    fallback = default_manager.get("nonexistent.agent.system")
    default = default_manager.get("default.system")
    assert fallback == default


def test_fallback_when_no_prompts_loaded() -> None:
    """Falls back to hardcoded string when no YAML was loaded."""
    manager = PromptManager(prompts_path=Path("/nonexistent/path.yaml"))
    result = manager.get("anything.system")
    assert "assistant" in result.lower() or len(result) > 0
