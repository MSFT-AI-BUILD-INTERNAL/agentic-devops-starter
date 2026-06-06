"""Tests for the Agent Skill Registry pattern."""

from pathlib import Path

import pytest

from src.skills import (
    DEFAULT_SKILLS_DIR,
    AgentSkill,
    SkillRegistry,
    build_default_registry,
    format_skills_context,
)

# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def test_default_registry_loads_bundled_skills() -> None:
    registry = build_default_registry()
    ids = {s.id for s in registry.list_all()}
    # Every shipped descriptor must be loaded.
    expected_files = {p.stem for p in DEFAULT_SKILLS_DIR.glob("*.json")}
    assert ids == expected_files
    assert len(registry) == len(expected_files)


def test_registry_get_returns_none_for_unknown() -> None:
    registry = build_default_registry()
    assert registry.get("does-not-exist") is None


def test_registry_contains_operator() -> None:
    registry = build_default_registry()
    sample_id = next(iter(registry.list_all())).id
    assert sample_id in registry
    assert "does-not-exist" not in registry


def test_register_overrides_existing(tmp_path: Path) -> None:
    registry = SkillRegistry()
    registry.register(
        AgentSkill(
            id="x",
            name="X",
            description="d",
            system_prompt="p",
            keywords=["alpha"],
        )
    )
    registry.register(
        AgentSkill(
            id="x",
            name="X2",
            description="d",
            system_prompt="p",
            keywords=[],
        )
    )
    assert registry.get("x") is not None
    assert registry.get("x").name == "X2"


def test_load_from_missing_directory_returns_zero(tmp_path: Path) -> None:
    registry = SkillRegistry()
    loaded = registry.load_from_directory(tmp_path / "missing")
    assert loaded == 0
    assert len(registry) == 0


def test_load_skips_invalid_descriptor(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    good.write_text(
        '{"id": "g", "name": "G", "description": "d", "system_prompt": "p"}',
        encoding="utf-8",
    )
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")

    registry = SkillRegistry()
    loaded = registry.load_from_directory(tmp_path)

    assert loaded == 1
    assert registry.get("g") is not None


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        AgentSkill(
            id="devops",
            name="DevOps",
            description="d",
            system_prompt="p",
            keywords=["deploy", "pipeline"],
        )
    )
    registry.register(
        AgentSkill(
            id="security",
            name="Sec",
            description="d",
            system_prompt="p",
            keywords=["security", "secret"],
        )
    )
    registry.register(
        AgentSkill(
            id="docs",
            name="Docs",
            description="d",
            system_prompt="p",
            keywords=["readme"],
        )
    )
    return registry


def test_select_for_matches_keywords(sample_registry: SkillRegistry) -> None:
    result = sample_registry.select_for("My deploy pipeline broke after a secret rotation")
    ids = [s.id for s in result]
    # devops matches twice (deploy + pipeline), security once -> devops first.
    assert ids[0] == "devops"
    assert "security" in ids
    assert "docs" not in ids


def test_select_for_is_case_insensitive(sample_registry: SkillRegistry) -> None:
    result = sample_registry.select_for("Please review the README")
    assert [s.id for s in result] == ["docs"]


def test_select_for_returns_empty_when_no_match(sample_registry: SkillRegistry) -> None:
    assert sample_registry.select_for("hello world") == []


def test_select_for_respects_limit(sample_registry: SkillRegistry) -> None:
    result = sample_registry.select_for(
        "deploy pipeline secret readme", limit=2
    )
    assert len(result) == 2


def test_select_for_empty_prompt(sample_registry: SkillRegistry) -> None:
    assert sample_registry.select_for("") == []


def test_resolve_silently_drops_unknown_ids(sample_registry: SkillRegistry) -> None:
    skills = sample_registry.resolve(["devops", "missing"])
    assert [s.id for s in skills] == ["devops"]


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------


def test_format_skills_context_empty() -> None:
    assert format_skills_context([]) == ""


def test_format_skills_context_includes_prompt(sample_registry: SkillRegistry) -> None:
    skills = sample_registry.resolve(["devops"])
    text = format_skills_context(skills)
    assert "Agent Skills Activated" in text
    assert "DevOps" in text
    assert "devops" in text
