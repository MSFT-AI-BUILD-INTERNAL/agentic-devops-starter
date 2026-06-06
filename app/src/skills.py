"""Agent Skill Registry pattern.

A *skill* is a reusable, domain-specific behavior — described in a small JSON
descriptor — that augments the AI agent's system prompt when it is relevant
to the customer's request. Skills are defined declaratively in
``app/src/skills_data`` and loaded once at application startup via
:class:`SkillRegistry`.

The registry exposes three primary operations used by the rest of the app:

* :meth:`SkillRegistry.list_all` — enumerate all known skills.
* :meth:`SkillRegistry.get` — fetch a specific skill by ``id``.
* :meth:`SkillRegistry.select_for` — keyword-match skills against a free-form
  customer prompt so the agent can opportunistically apply relevant skills.

The design intentionally stays dependency-free (stdlib + pydantic) so the
registry can be reused from FastAPI handlers, background jobs, and unit
tests without any I/O setup beyond reading the bundled JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from src.logging_utils import setup_logging

logger = setup_logging()


DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent / "skills_data"


class AgentSkill(BaseModel):
    """Declarative description of a reusable agent capability."""

    id: str
    name: str
    description: str
    system_prompt: str
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"


class SkillRegistry:
    """In-memory registry of :class:`AgentSkill` definitions.

    Implements the Registry Pattern: a single source of truth for all
    skills known to the application. Loading is explicit so callers can
    point the registry at a custom directory (for example, in tests).
    """

    def __init__(self) -> None:
        self._skills: dict[str, AgentSkill] = {}

    # ----- loading -----------------------------------------------------

    def load_from_directory(self, directory: Path) -> int:
        """Load every ``*.json`` skill descriptor from *directory*.

        Returns the number of skills loaded. Invalid files are logged and
        skipped so a single bad descriptor cannot crash startup.
        """
        if not directory.exists() or not directory.is_dir():
            logger.warning("Skill directory not found: %s", directory)
            return 0

        loaded = 0
        for path in sorted(directory.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                skill = AgentSkill.model_validate(data)
            except Exception:
                logger.exception("Failed to load skill descriptor: %s", path)
                continue

            if skill.id in self._skills:
                logger.warning(
                    "Duplicate skill id %r in %s — overriding previous entry",
                    skill.id,
                    path.name,
                )
            self._skills[skill.id] = skill
            loaded += 1

        logger.info("Loaded %d agent skill(s) from %s", loaded, directory)
        return loaded

    def register(self, skill: AgentSkill) -> None:
        """Programmatically register a skill (useful in tests)."""
        self._skills[skill.id] = skill

    # ----- lookups -----------------------------------------------------

    def list_all(self) -> list[AgentSkill]:
        """Return all registered skills, ordered by id."""
        return [self._skills[k] for k in sorted(self._skills)]

    def get(self, skill_id: str) -> AgentSkill | None:
        """Return the skill with *skill_id*, or ``None`` if unknown."""
        return self._skills.get(skill_id)

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, skill_id: object) -> bool:
        return isinstance(skill_id, str) and skill_id in self._skills

    # ----- selection ---------------------------------------------------

    def select_for(self, prompt: str, limit: int = 3) -> list[AgentSkill]:
        """Return skills whose keywords appear in *prompt*.

        Matching is case-insensitive substring matching on whole keywords.
        Skills are ranked by the number of distinct matching keywords
        (descending), then by ``id`` for stability. At most *limit*
        skills are returned to avoid overwhelming the model context.
        """
        if not prompt or limit <= 0:
            return []

        haystack = prompt.lower()
        scored: list[tuple[int, str, AgentSkill]] = []
        for skill in self._skills.values():
            hits = sum(1 for kw in skill.keywords if kw and kw.lower() in haystack)
            if hits > 0:
                scored.append((hits, skill.id, skill))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [skill for _, _, skill in scored[:limit]]

    def resolve(self, skill_ids: list[str]) -> list[AgentSkill]:
        """Return the skills matching *skill_ids*, silently dropping unknowns."""
        resolved: list[AgentSkill] = []
        for sid in skill_ids:
            skill = self._skills.get(sid)
            if skill is not None:
                resolved.append(skill)
            else:
                logger.warning("Unknown skill id requested: %r", sid)
        return resolved


def build_default_registry(directory: Path | None = None) -> SkillRegistry:
    """Create a :class:`SkillRegistry` pre-loaded with the bundled skills."""
    registry = SkillRegistry()
    registry.load_from_directory(directory or DEFAULT_SKILLS_DIR)
    return registry


def format_skills_context(skills: list[AgentSkill]) -> str:
    """Format selected skills as a system-prompt prefix block.

    Returns an empty string when no skills are provided so callers can
    safely concatenate without worrying about leading whitespace.
    """
    if not skills:
        return ""

    lines = ["[Agent Skills Activated]"]
    for skill in skills:
        lines.append(f"- {skill.name} ({skill.id}): {skill.system_prompt}")
    return "\n".join(lines)
