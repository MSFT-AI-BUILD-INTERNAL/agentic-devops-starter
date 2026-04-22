"""Tests for SkillRegistry and HarnessHook."""

import pytest

from src.agents.tools import (
    AgentSkill,
    CalculatorSkill,
    SkillDefinition,
    SkillRegistry,
    WeatherSkill,
    build_default_registry,
)
from src.hooks.harness_hook import HarnessHook, HarnessReport, HarnessViolationError

# ===========================================================================
# SkillRegistry
# ===========================================================================


def test_build_default_registry_contains_built_in_skills() -> None:
    """build_default_registry() must include 'calculator' and 'get_weather'."""
    registry = build_default_registry()
    names = [s.name for s in registry.list_skills()]
    assert "calculator" in names
    assert "get_weather" in names


def test_registry_register_and_get() -> None:
    """Registered skills must be retrievable by name."""
    registry = SkillRegistry()
    skill = CalculatorSkill()
    registry.register(skill)

    retrieved = registry.get("calculator")
    assert retrieved is skill


def test_registry_get_missing_skill_returns_none() -> None:
    """Getting an unregistered skill must return None."""
    registry = SkillRegistry()
    assert registry.get("nonexistent") is None


def test_registry_list_skills() -> None:
    """list_skills() must return SkillDefinition objects for all registered skills."""
    registry = SkillRegistry()
    registry.register(CalculatorSkill())
    registry.register(WeatherSkill())

    definitions = registry.list_skills()
    assert len(definitions) == 2
    assert all(isinstance(d, SkillDefinition) for d in definitions)


def test_skill_definition_has_examples() -> None:
    """AgentSkill.get_definition() must return at least one example."""
    for skill_cls in (CalculatorSkill, WeatherSkill):
        definition = skill_cls().get_definition()
        assert len(definition.examples) >= 1, f"{skill_cls.__name__} must have at least one example"


def test_calculator_skill_inherits_agent_skill() -> None:
    """CalculatorSkill must inherit from AgentSkill."""
    assert issubclass(CalculatorSkill, AgentSkill)


def test_weather_skill_inherits_agent_skill() -> None:
    """WeatherSkill must inherit from AgentSkill."""
    assert issubclass(WeatherSkill, AgentSkill)


def test_calculator_skill_executes_correctly() -> None:
    """CalculatorSkill.execute() must return correct results."""
    skill = CalculatorSkill()
    result = skill.execute(operation="add", a=3, b=4)
    assert result["result"] == 7


def test_weather_skill_executes_correctly() -> None:
    """WeatherSkill.execute() must return a location entry."""
    skill = WeatherSkill()
    result = skill.execute(location="Seattle")
    assert result["location"] == "Seattle"
    assert "temperature" in result


# ===========================================================================
# HarnessHook
# ===========================================================================


def test_harness_hook_returns_report() -> None:
    """HarnessHook.run() must return a HarnessReport."""
    hook = HarnessHook()
    report = hook.run("Hello", "Hello back!")
    assert isinstance(report, HarnessReport)


def test_harness_hook_passes_clean_content() -> None:
    """Clean input and output must produce a passing report."""
    hook = HarnessHook()
    report = hook.run("What is the weather?", "It is sunny in Seattle.")
    assert report.passed is True
    assert report.has_violations is False
    assert report.violation_count == 0


def test_harness_hook_detects_input_violation() -> None:
    """A blocked command in input must appear in the report violations."""
    hook = HarnessHook()
    report = hook.run("sudo rm -rf /", "I cannot do that.")
    assert report.passed is False
    assert report.has_violations is True
    assert report.violation_count >= 1


def test_harness_hook_detects_output_violation() -> None:
    """Sensitive data in output must appear in the report violations."""
    hook = HarnessHook()
    report = hook.run("What is my password?", "Your password: hunter2")
    assert report.passed is False
    assert report.has_violations is True


def test_harness_hook_observe_mode_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """In observe mode (default), violations must not raise HarnessViolationError."""
    hook = HarnessHook(fail_on_violation=False)
    # Should not raise even with a violation
    report = hook.run("sudo rm -rf /", "safe response")
    assert report.has_violations is True


def test_harness_hook_enforce_mode_raises_on_violation() -> None:
    """In enforce mode, a violation must raise HarnessViolationError."""
    hook = HarnessHook(fail_on_violation=True)
    with pytest.raises(HarnessViolationError):
        hook.run("sudo rm -rf /", "safe response")


def test_harness_report_properties() -> None:
    """HarnessReport must expose passed, violations, violation_count, has_violations."""
    report = HarnessReport(passed=False, violations=["blocked command: sudo"])
    assert report.passed is False
    assert report.has_violations is True
    assert report.violation_count == 1
    assert "sudo" in report.violations[0]


def test_harness_report_preserves_io() -> None:
    """HarnessReport must preserve user_input and agent_output."""
    hook = HarnessHook()
    report = hook.run("user msg", "agent reply")
    assert report.user_input == "user msg"
    assert report.agent_output == "agent reply"
