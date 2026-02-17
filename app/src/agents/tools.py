"""Tool definitions for agent framework demonstration."""

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


class ToolDefinition(BaseModel):
    """Tool definition with name, description, and parameters."""
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(default_factory=dict)


class Tool(ABC):
    """Abstract base class for agent tools."""

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        pass


class CalculatorTool(Tool):
    """Calculator tool for basic arithmetic."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="Perform basic arithmetic operations",
            parameters={
                "operation": {
                    "type": "string",
                    "enum": [op.value for op in ArithmeticOperation]
                },
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
        )

    def execute(self, operation: str, a: float, b: float) -> dict[str, Any]:
        ops = {
            ArithmeticOperation.ADD: lambda x, y: x + y,
            ArithmeticOperation.SUBTRACT: lambda x, y: x - y,
            ArithmeticOperation.MULTIPLY: lambda x, y: x * y,
            ArithmeticOperation.DIVIDE: lambda x, y: x / y if y != 0 else None,
        }

        # Normalize operation to enum
        try:
            op_enum = ArithmeticOperation(operation)
        except ValueError as err:
            raise ValueError(f"Invalid operation: {operation}") from err

        result = ops[op_enum](a, b)
        if result is None:
            raise ValueError("Division by zero")
        return {"operation": operation, "operands": [a, b], "result": result}


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
