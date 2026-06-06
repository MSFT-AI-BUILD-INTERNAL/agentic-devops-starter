"""Tests for the Agent Skills loader.

Validates that the application discovers the predefined SKILL.md skills
shipped under ``app/skills/`` and exposes them for the Copilot SDK without
acting as a registry.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import src.skills as skills_module
from src.skills import (
    get_disabled_skills,
    get_loaded_skill_names,
    get_skill_directories,
    load_skills,
)

REPO_SKILLS = (Path(__file__).resolve().parent.parent / "skills").resolve()


def _reset_cache() -> None:
    skills_module._skill_directories = []
    skills_module._loaded_skill_names = []


def test_repo_skills_directory_exists() -> None:
    """Shipped skills directory must exist with at least one SKILL.md."""
    assert REPO_SKILLS.is_dir(), f"missing {REPO_SKILLS}"
    skill_files = list(REPO_SKILLS.glob("*/SKILL.md"))
    assert skill_files, "no predefined SKILL.md files were shipped"


def test_predefined_skills_have_required_frontmatter() -> None:
    """Each SKILL.md must declare ``name`` and ``description`` so the SDK
    can route to it."""
    for skill_md in REPO_SKILLS.glob("*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"missing YAML frontmatter in {skill_md}"
        head, _, _ = text[4:].partition("\n---\n")
        assert "name:" in head, f"missing 'name:' in {skill_md}"
        assert "description:" in head, f"missing 'description:' in {skill_md}"


def test_load_skills_discovers_repo_directory() -> None:
    _reset_cache()
    dirs = load_skills()
    try:
        assert str(REPO_SKILLS) in dirs
        names = get_loaded_skill_names()
        assert "code-reviewer" in names
        assert "devops-troubleshooter" in names
        assert "secure-coding-advisor" in names
        # get_skill_directories returns the cached list
        assert get_skill_directories() == dirs
    finally:
        _reset_cache()


def test_load_skills_includes_extra_env_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    extra = tmp_path / "extra"
    (extra / "my-skill").mkdir(parents=True)
    (extra / "my-skill" / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: extra test skill\n---\nbody\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skills_module.settings, "skill_directories", str(extra))
    _reset_cache()
    try:
        dirs = load_skills()
        assert str(extra.resolve()) in dirs
        assert "my-skill" in get_loaded_skill_names()
    finally:
        _reset_cache()


def test_load_skills_skips_missing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-existent extra directories must not crash discovery."""
    monkeypatch.setattr(
        skills_module.settings, "skill_directories", str(tmp_path / "does-not-exist")
    )
    _reset_cache()
    try:
        dirs = load_skills()
        # Repo skills still loaded; bogus directory is silently skipped.
        assert str(REPO_SKILLS) in dirs
        assert all("does-not-exist" not in d for d in dirs)
    finally:
        _reset_cache()


def test_disabled_skills_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(skills_module.settings, "disabled_skills", "a, b ,c")
    assert get_disabled_skills() == ["a", "b", "c"]
    monkeypatch.setattr(skills_module.settings, "disabled_skills", "")
    assert get_disabled_skills() == []


def test_get_skill_directories_empty_before_load() -> None:
    _reset_cache()
    assert get_skill_directories() == []
    assert get_loaded_skill_names() == []
