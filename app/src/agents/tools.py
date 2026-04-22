"""Tool and skill definitions for agent framework demonstration."""

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


_ARITHMETIC_OPS: dict[ArithmeticOperation, Any] = {
    ArithmeticOperation.ADD: lambda x, y: x + y,
    ArithmeticOperation.SUBTRACT: lambda x, y: x - y,
    ArithmeticOperation.MULTIPLY: lambda x, y: x * y,
    ArithmeticOperation.DIVIDE: lambda x, y: x / y if y != 0 else None,
}


def _run_arithmetic(operation: str, a: float, b: float) -> dict[str, Any]:
    """Shared helper for arithmetic operations used by both CalculatorTool and CalculatorSkill."""
    try:
        op_enum = ArithmeticOperation(operation)
    except ValueError as err:
        raise ValueError(f"Invalid operation: {operation}") from err

    result = _ARITHMETIC_OPS[op_enum](a, b)
    if result is None:
        raise ValueError("Division by zero")
    return {"operation": operation, "operands": [a, b], "result": result}


class ToolDefinition(BaseModel):
    """Tool definition with name, description, and parameters."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(default_factory=dict)


class SkillDefinition(BaseModel):
    """Skill definition with name, description, parameters, and usage examples."""

    name: str = Field(description="Skill name")
    description: str = Field(description="Skill description")
    parameters: dict[str, Any] = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list, description="Usage examples")


class Tool(ABC):
    """Abstract base class for agent tools."""

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        pass


class AgentSkill(ABC):
    """Abstract base class for agent skills.

    Inheriting classes must implement ``get_definition()`` (which must include
    at least one ``examples`` entry) and ``execute()``.  Skills are registered
    in a ``SkillRegistry`` and surfaced to the agent via
    ``agent.describe_skills()``.
    """

    @abstractmethod
    def get_definition(self) -> SkillDefinition:
        """Return the skill metadata including name, description, parameters, and examples."""

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the skill logic."""


class CalculatorTool(Tool):
    """Calculator tool for basic arithmetic."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="Perform basic arithmetic operations",
            parameters={
                "operation": {
                    "type": "string",
                    "enum": [op.value for op in ArithmeticOperation],
                },
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
        )

    def execute(self, operation: str, a: float, b: float) -> dict[str, Any]:
        return _run_arithmetic(operation, a, b)


class WeatherTool(Tool):
    """Weather tool (mock implementation)."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_weather",
            description="Get weather for a location",
            parameters={"location": {"type": "string"}},
        )

    def execute(self, location: str) -> dict[str, Any]:
        return {
            "location": location,
            "temperature": 72,
            "conditions": "Partly cloudy",
            "note": "Mock data",
        }


class CalculatorSkill(AgentSkill):
    """Calculator skill for basic arithmetic (add, subtract, multiply, divide)."""

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="calculator",
            description="Perform basic arithmetic operations (add, subtract, multiply, divide)",
            parameters={
                "operation": {
                    "type": "string",
                    "enum": [op.value for op in ArithmeticOperation],
                },
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            examples=[
                "calculator(operation='add', a=3, b=4) → {'result': 7}",
                "calculator(operation='divide', a=10, b=2) → {'result': 5.0}",
            ],
        )

    def execute(self, operation: str, a: float, b: float) -> dict[str, Any]:  # type: ignore[override]
        return _run_arithmetic(operation, a, b)


class WeatherSkill(AgentSkill):
    """Weather skill for looking up weather information for a city or location."""

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="get_weather",
            description="Get the current weather for a city or location",
            parameters={"location": {"type": "string"}},
            examples=[
                "get_weather(location='Seattle') → {'temperature': 55, 'conditions': 'Rainy'}",
                "get_weather(location='London') → {'temperature': 60, 'conditions': 'Cloudy'}",
            ],
        )

    def execute(self, location: str) -> dict[str, Any]:  # type: ignore[override]
        return {
            "location": location,
            "temperature": 72,
            "conditions": "Partly cloudy",
            "note": "Mock data",
        }


class SkillRegistry:
    """Registry for agent skills.

    Skills are registered by name.  Use ``build_default_registry()`` to obtain
    a pre-populated instance with the built-in skills.
    """

    def __init__(self) -> None:
        self._skills: dict[str, AgentSkill] = {}

    def register(self, skill: AgentSkill) -> None:
        """Register a skill.

        Args:
            skill: The skill instance to register.
        """
        definition = skill.get_definition()
        self._skills[definition.name] = skill

    def get(self, name: str) -> AgentSkill | None:
        """Return the skill registered under *name*, or ``None``."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillDefinition]:
        """Return definitions for all registered skills."""
        return [skill.get_definition() for skill in self._skills.values()]


def build_default_registry() -> SkillRegistry:
    """Build and return a ``SkillRegistry`` pre-populated with built-in skills."""
    registry = SkillRegistry()
    registry.register(CalculatorSkill())
    registry.register(WeatherSkill())
    return registry
