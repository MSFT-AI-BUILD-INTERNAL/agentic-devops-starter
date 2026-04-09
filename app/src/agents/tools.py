"""AgentSkill definitions and registry for the agent framework.

Skills are first-class capabilities that agents actively discover and invoke.
Each skill declares its interface via ``SkillDefinition`` and implements
``execute()`` for runtime invocation.  The ``SkillRegistry`` acts as a
central catalogue so agents can list, look up, and call skills by name.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ArithmeticOperation(StrEnum):
    """Supported arithmetic operations."""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class SkillDefinition(BaseModel):
    """Metadata describing an agent skill."""

    name: str = Field(description="Unique skill name")
    description: str = Field(description="What the skill does")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Input parameter schema")
    examples: list[str] = Field(
        default_factory=list,
        description="Example invocations that help the agent decide when to use this skill",
    )


# Keep the legacy alias so existing callers that import ToolDefinition still work.
ToolDefinition = SkillDefinition


class AgentSkill(ABC):
    """Abstract base class for agent skills (replaces Tool).

    Every concrete skill must implement:
    - ``get_definition()`` — returns :class:`SkillDefinition` metadata.
    - ``execute(**kwargs)`` — carries out the skill action.
    """

    @abstractmethod
    def get_definition(self) -> SkillDefinition:
        """Return the skill definition/metadata."""

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the skill with the provided arguments."""


# Keep the legacy alias so existing callers that import Tool still work.
Tool = AgentSkill


class SkillRegistry:
    """Central registry that agents use to discover and invoke skills.

    Usage::

        registry = SkillRegistry()
        registry.register(CalculatorSkill())
        skill = registry.get("calculator")
        result = skill.execute(operation="add", a=3, b=4)
    """

    def __init__(self) -> None:
        self._skills: dict[str, AgentSkill] = {}

    def register(self, skill: AgentSkill) -> None:
        """Register a skill.  Raises ``ValueError`` on duplicate names."""
        name = skill.get_definition().name
        if name in self._skills:
            raise ValueError(f"Skill '{name}' is already registered")
        self._skills[name] = skill

    def get(self, name: str) -> AgentSkill:
        """Return the skill with the given name.

        Raises:
            KeyError: If no skill with that name is registered.
        """
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' is not registered")
        return self._skills[name]

    def list_skills(self) -> list[SkillDefinition]:
        """Return definitions for all registered skills."""
        return [s.get_definition() for s in self._skills.values()]

    def describe(self) -> str:
        """Return a human-readable summary of available skills for prompt injection."""
        lines: list[str] = ["Available skills:"]
        for defn in self.list_skills():
            lines.append(f"  - {defn.name}: {defn.description}")
            if defn.examples:
                lines.append(f"    Examples: {'; '.join(defn.examples)}")
        return "\n".join(lines)


class CalculatorSkill(AgentSkill):
    """Calculator skill for basic arithmetic."""

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="calculator",
            description="Perform basic arithmetic operations (add, subtract, multiply, divide)",
            parameters={
                "operation": {
                    "type": "string",
                    "enum": [op.value for op in ArithmeticOperation],
                },
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand"},
            },
            examples=[
                "calculator(operation='add', a=5, b=3) → 8",
                "calculator(operation='divide', a=10, b=2) → 5",
            ],
        )

    def execute(self, operation: str, a: float, b: float) -> dict[str, Any]:  # type: ignore[override]  # narrower sig is intentional
        ops = {
            ArithmeticOperation.ADD: lambda x, y: x + y,
            ArithmeticOperation.SUBTRACT: lambda x, y: x - y,
            ArithmeticOperation.MULTIPLY: lambda x, y: x * y,
            ArithmeticOperation.DIVIDE: lambda x, y: x / y if y != 0 else None,
        }
        try:
            op_enum = ArithmeticOperation(operation)
        except ValueError as err:
            raise ValueError(f"Invalid operation: {operation}") from err
        result = ops[op_enum](a, b)
        if result is None:
            raise ValueError("Division by zero")
        return {"operation": operation, "operands": [a, b], "result": result}


# Legacy alias — keeps existing imports of CalculatorTool working.
CalculatorTool = CalculatorSkill


class WeatherSkill(AgentSkill):
    """Weather skill (mock implementation)."""

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="get_weather",
            description="Get current weather conditions for a city or location",
            parameters={"location": {"type": "string", "description": "City or location name"}},
            examples=[
                "get_weather(location='Seattle') → temperature, conditions",
                "get_weather(location='London') → temperature, conditions",
            ],
        )

    def execute(self, location: str) -> dict[str, Any]:  # type: ignore[override]  # narrower sig is intentional
        return {
            "location": location,
            "temperature": 72,
            "conditions": "Partly cloudy",
            "note": "Mock data",
        }


# Legacy alias — keeps existing imports of WeatherTool working.
WeatherTool = WeatherSkill


def build_default_registry() -> SkillRegistry:
    """Return a ``SkillRegistry`` pre-loaded with the built-in skills."""
    registry = SkillRegistry()
    registry.register(CalculatorSkill())
    registry.register(WeatherSkill())
    return registry
