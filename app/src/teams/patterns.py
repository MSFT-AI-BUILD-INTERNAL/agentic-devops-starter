"""Agent team pattern definitions."""

from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, ValidationError


class AgentRole(BaseModel):
    """A single role within a multi-agent pattern."""

    name: str = Field(min_length=1)
    emoji: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)


class Pattern(BaseModel):
    """A multi-agent collaboration pattern."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    roles: list[AgentRole] = Field(min_length=1)
    flow_type: str = Field(min_length=1)
    max_rounds: int = 3


PATTERN_DATA_PATH = files("src.teams.data").joinpath("patterns.yaml")
EXPECTED_PATTERN_IDS = (
    "debate-critic",
    "generator-evaluator",
    "leadership",
    "planner-executor",
    "research-report",
)
_REQUIRED_PATTERN_FIELDS = frozenset(
    {"id", "name", "description", "roles", "flow_type", "max_rounds"}
)


def _read_pattern_registry(path: Traversable) -> Any:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to load pattern registry YAML: {path}") from exc

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Invalid pattern registry YAML: {path}") from exc


def _pattern_data(raw_pattern: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw_pattern, dict):
        raise ValueError(f"Invalid pattern at index {index}: expected mapping")

    missing_fields = _REQUIRED_PATTERN_FIELDS - raw_pattern.keys()
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Invalid pattern at index {index}: missing required fields: {missing}")

    return raw_pattern


def _load_pattern_registry(path: Traversable = PATTERN_DATA_PATH) -> dict[str, Pattern]:
    """Load and validate predefined patterns from YAML."""
    raw_registry = _read_pattern_registry(path)
    if not isinstance(raw_registry, dict):
        raise ValueError("Pattern registry YAML must contain a mapping")

    raw_patterns = raw_registry.get("patterns")
    if not isinstance(raw_patterns, list):
        raise ValueError("Pattern registry YAML must contain a 'patterns' list")

    patterns: dict[str, Pattern] = {}
    for index, raw_pattern in enumerate(raw_patterns):
        try:
            pattern = Pattern.model_validate(_pattern_data(raw_pattern, index))
        except ValidationError as exc:
            raise ValueError(f"Invalid pattern at index {index}: {exc}") from exc

        if pattern.id in patterns:
            raise ValueError(f"Duplicate pattern id: {pattern.id}")
        patterns[pattern.id] = pattern

    pattern_ids = tuple(patterns)
    if pattern_ids != EXPECTED_PATTERN_IDS:
        expected = ", ".join(EXPECTED_PATTERN_IDS)
        actual = ", ".join(pattern_ids)
        raise ValueError(
            "Pattern registry must define exactly these IDs in order: "
            f"{expected}; got: {actual}"
        )

    return patterns


PATTERNS: dict[str, Pattern] = _load_pattern_registry()


def get_pattern(pattern_id: str) -> Pattern | None:
    """Return a pattern by ID, or None if not found."""
    return PATTERNS.get(pattern_id)
