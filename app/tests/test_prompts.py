"""Tests for the centralized prompt manager."""

from pathlib import Path

import pytest

from src.prompts.prompt_manager import PromptManager, _parse_yaml_prompts

# ---------------------------------------------------------------------------
# YAML parser unit tests
# ---------------------------------------------------------------------------

def test_parse_yaml_prompts_basic() -> None:
    """Parser should extract key→value pairs from block scalar YAML."""
    content = (
        "prompts:\n"
        "  foo.system: |\n"
        "    Hello world\n"
        "    Second line\n"
        "  bar.system: |\n"
        "    Another prompt\n"
    )
    result = _parse_yaml_prompts(content)
    assert "foo.system" in result
    assert "bar.system" in result
    assert "Hello world" in result["foo.system"]
    assert "Second line" in result["foo.system"]
    assert "Another prompt" in result["bar.system"]


def test_parse_yaml_prompts_empty() -> None:
    """Parser should return an empty dict for content with no prompt entries."""
    result = _parse_yaml_prompts("prompts:\n")
    assert result == {}


# ---------------------------------------------------------------------------
# PromptManager with the real system_prompts.yaml
# ---------------------------------------------------------------------------

@pytest.fixture
def manager() -> PromptManager:
    """Return a PromptManager backed by the real system_prompts.yaml."""
    return PromptManager()


def test_manager_loads_default_prompt(manager: PromptManager) -> None:
    """The default.system prompt should be available."""
    prompt = manager.get("default.system")
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_manager_loads_agui_assistant_prompt(manager: PromptManager) -> None:
    """The agui_assistant.system prompt should be available and non-empty."""
    prompt = manager.get("agui_assistant.system")
    assert "AI assistant" in prompt


def test_manager_loads_conversational_prompt(manager: PromptManager) -> None:
    """The conversational.system prompt should be available."""
    prompt = manager.get("conversational.system")
    assert len(prompt) > 0


def test_manager_falls_back_to_default(manager: PromptManager) -> None:
    """An unknown key should fall back to the default.system prompt."""
    prompt = manager.get("nonexistent.prompt.key")
    default_prompt = manager.get("default.system")
    assert prompt == default_prompt


def test_manager_list_keys(manager: PromptManager) -> None:
    """list_keys() should include at least the expected built-in keys."""
    keys = manager.list_keys()
    assert "default.system" in keys
    assert "agui_assistant.system" in keys
    assert "conversational.system" in keys


def test_manager_raises_when_no_default(tmp_path: Path) -> None:
    """PromptManager should raise KeyError when neither key nor default exists."""
    yaml_content = (
        "prompts:\n"
        "  only.key: |\n"
        "    Some prompt\n"
    )
    yaml_file = tmp_path / "prompts.yaml"
    yaml_file.write_text(yaml_content)
    manager = PromptManager(yaml_path=yaml_file)
    with pytest.raises(KeyError):
        manager.get("missing.key")


def test_manager_custom_yaml(tmp_path: Path) -> None:
    """PromptManager should load prompts from a custom YAML file."""
    yaml_content = (
        "prompts:\n"
        "  default.system: |\n"
        "    Default fallback\n"
        "  custom.agent: |\n"
        "    Custom agent prompt here\n"
    )
    yaml_file = tmp_path / "custom_prompts.yaml"
    yaml_file.write_text(yaml_content)
    manager = PromptManager(yaml_path=yaml_file)
    assert manager.get("custom.agent") == "Custom agent prompt here"
    assert manager.get("default.system") == "Default fallback"
