"""Agent Skills loader.

Discovers on-disk Agent Skills (open SKILL.md format) and exposes the
directories that should be passed to the GitHub Copilot SDK so it can load
and apply them.

The application is intentionally **not** a skill registry: it neither lists
nor serves skills over an API. It only resolves the filesystem locations
the SDK should scan for ``SKILL.md`` files.

A skill is a folder containing a ``SKILL.md`` file with YAML frontmatter
(``name``, ``description`` at minimum) followed by a Markdown instruction
body. See ``app/skills/README.md`` for examples.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from src.config import settings
from src.logging_utils import setup_logging

logger = setup_logging(settings.log_level)

# Built-in skills directory shipped with the application.
_REPO_SKILLS_DIR = (Path(__file__).resolve().parent.parent / "skills").resolve()

# Skill discovery is performed once at startup and cached.
_skill_directories: list[str] = []
_loaded_skill_names: list[str] = []


def _extra_directories_from_env() -> list[Path]:
    """Return additional skill directories from the env-configured setting."""
    raw = settings.skill_directories
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(",", os.pathsep).split(os.pathsep)]
    return [Path(p).expanduser().resolve() for p in parts if p]


def _has_any_skill(directory: Path) -> bool:
    """Return True if *directory* contains at least one ``<name>/SKILL.md``."""
    if not directory.is_dir():
        return False
    for entry in directory.iterdir():
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            return True
    return False


def _enumerate_skill_names(directories: Iterable[Path]) -> list[str]:
    """Return sorted unique skill folder names found under *directories*."""
    names: set[str] = set()
    for d in directories:
        if not d.is_dir():
            continue
        for entry in d.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                names.add(entry.name)
    return sorted(names)


def load_skills() -> list[str]:
    """Resolve and cache the list of skill directories for the Copilot SDK.

    Called once during application startup. Logs how many skills were
    discovered. Missing or empty directories are skipped (not an error).

    Returns the resolved list of directory paths (as strings).
    """
    global _skill_directories, _loaded_skill_names

    candidates: list[Path] = [_REPO_SKILLS_DIR, *_extra_directories_from_env()]

    resolved: list[str] = []
    seen: set[str] = set()
    for directory in candidates:
        if not _has_any_skill(directory):
            logger.debug(
                "Skipping skill directory (missing or no SKILL.md)",
                extra={"skill_directory": str(directory)},
            )
            continue
        key = str(directory)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(key)

    _skill_directories = resolved
    _loaded_skill_names = _enumerate_skill_names(Path(p) for p in resolved)

    logger.info(
        "Agent Skills loaded",
        extra={
            "skill_directories": _skill_directories,
            "skill_names": _loaded_skill_names,
            "skill_count": len(_loaded_skill_names),
        },
    )
    return _skill_directories


def get_skill_directories() -> list[str]:
    """Return the cached skill directories (empty list if none loaded)."""
    return list(_skill_directories)


def get_disabled_skills() -> list[str]:
    """Return skill names the operator has opted to disable."""
    raw = settings.disabled_skills
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def get_loaded_skill_names() -> list[str]:
    """Return skill names discovered on disk (post-``load_skills``)."""
    return list(_loaded_skill_names)
