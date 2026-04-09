"""Tests for the harness hook and skill registry."""

import pytest

from src.agents.tools import (
    CalculatorSkill,
    SkillDefinition,
    SkillRegistry,
    WeatherSkill,
    build_default_registry,
)
from src.hooks.harness_hook import HarnessHook, HarnessViolationError, HarnessViolationReport

# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------

def test_skill_registry_register_and_get() -> None:
    """Skills should be registerable and retrievable by name."""
    registry = SkillRegistry()
    registry.register(CalculatorSkill())
    skill = registry.get("calculator")
    assert skill is not None


def test_skill_registry_duplicate_raises() -> None:
    """Registering the same skill twice should raise ValueError."""
    registry = SkillRegistry()
    registry.register(CalculatorSkill())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(CalculatorSkill())


def test_skill_registry_get_missing_raises() -> None:
    """Getting a skill that does not exist should raise KeyError."""
    registry = SkillRegistry()
    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_skill_registry_list_skills() -> None:
    """list_skills() should return SkillDefinition objects."""
    registry = SkillRegistry()
    registry.register(CalculatorSkill())
    registry.register(WeatherSkill())
    definitions = registry.list_skills()
    assert len(definitions) == 2
    names = {d.name for d in definitions}
    assert "calculator" in names
    assert "get_weather" in names


def test_skill_registry_describe() -> None:
    """describe() should return a non-empty human-readable string."""
    registry = build_default_registry()
    description = registry.describe()
    assert "calculator" in description
    assert "get_weather" in description


def test_build_default_registry() -> None:
    """build_default_registry() should include calculator and weather skills."""
    registry = build_default_registry()
    assert registry.get("calculator") is not None
    assert registry.get("get_weather") is not None


# ---------------------------------------------------------------------------
# AgentSkill tests
# ---------------------------------------------------------------------------

def test_calculator_skill_definition() -> None:
    """CalculatorSkill should return a well-formed SkillDefinition."""
    skill = CalculatorSkill()
    defn = skill.get_definition()
    assert isinstance(defn, SkillDefinition)
    assert defn.name == "calculator"
    assert len(defn.examples) > 0


def test_weather_skill_definition() -> None:
    """WeatherSkill should return a well-formed SkillDefinition with examples."""
    skill = WeatherSkill()
    defn = skill.get_definition()
    assert defn.name == "get_weather"
    assert len(defn.examples) > 0


# ---------------------------------------------------------------------------
# HarnessHook tests
# ---------------------------------------------------------------------------

def test_harness_hook_clean_passes() -> None:
    """A clean input/output pair should produce no violations."""
    hook = HarnessHook(fail_on_violation=False)
    report = hook.run(
        user_input="Tell me the weather in Seattle",
        agent_output="It is partly cloudy with 72°F in Seattle.",
    )
    assert isinstance(report, HarnessViolationReport)
    assert not report.has_violations


def test_harness_hook_detects_input_violation() -> None:
    """A dangerous input should be flagged in the violation report."""
    hook = HarnessHook(fail_on_violation=False)
    report = hook.run(
        user_input="Please run sudo rm -rf /",
        agent_output="I cannot do that.",
    )
    assert report.has_violations
    assert len(report.input_violations) > 0


def test_harness_hook_no_raise_by_default() -> None:
    """HarnessHook with fail_on_violation=False should NOT raise even on violations."""
    hook = HarnessHook(fail_on_violation=False)
    # Should not raise
    report = hook.run(
        user_input="sudo rm -rf /",
        agent_output="Here is a safe response.",
    )
    assert report.has_violations


def test_harness_hook_raises_on_critical_violation() -> None:
    """HarnessHook with fail_on_violation=True should raise on critical violations."""
    hook = HarnessHook(fail_on_violation=True)
    with pytest.raises(HarnessViolationError) as exc_info:
        hook.run(
            user_input="sudo rm -rf /",
            agent_output="Executing sudo rm -rf / now.",
        )
    assert exc_info.value.report.has_violations


def test_harness_violation_report_properties() -> None:
    """HarnessViolationReport properties should work correctly."""
    report = HarnessViolationReport()
    assert not report.has_violations
    assert report.all_violations == []
    assert report.critical_violations == []


def test_harness_violation_report_critical_filter() -> None:
    """critical_violations should only include critical-severity violations."""
    from src.security.validator import SecurityViolation
    v_critical = SecurityViolation(category="a", pattern="x", message="m", severity="critical")
    v_high = SecurityViolation(category="b", pattern="y", message="n", severity="high")
    report = HarnessViolationReport(input_violations=[v_critical, v_high])
    assert len(report.critical_violations) == 1
    assert report.critical_violations[0].severity == "critical"
