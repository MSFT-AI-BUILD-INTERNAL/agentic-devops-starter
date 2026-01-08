"""Tool integration for agent framework.

This module demonstrates how to integrate tools/functions with agents
following the microsoft-agent-framework patterns.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Definition of a tool that can be used by an agent.

    Tools allow agents to perform actions beyond simple text generation,
    such as retrieving data, performing calculations, or interacting with APIs.
    """

    name: str = Field(
        description="Unique name for the tool"
    )
    description: str = Field(
        description="Description of what the tool does"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter schema for the tool"
    )


class Tool(ABC):
    """Abstract base class for agent tools."""

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Get the tool definition.

        Returns:
            Tool definition with name, description, and parameters
        """
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool with given parameters.

        Args:
            *args: Positional arguments for the tool
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result
        """
        pass


class CalculatorTool(Tool):
    """Example tool for performing calculations."""

    def get_definition(self) -> ToolDefinition:
        """Get calculator tool definition.

        Returns:
            Tool definition for calculator
        """
        return ToolDefinition(
            name="calculator",
            description="Perform basic arithmetic operations",
            parameters={
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The arithmetic operation to perform"
                },
                "a": {
                    "type": "number",
                    "description": "First operand"
                },
                "b": {
                    "type": "number",
                    "description": "Second operand"
                }
            }
        )

    def execute(self, operation: str, a: float, b: float) -> dict[str, Any]:
        """Execute calculator operation.

        Args:
            operation: Operation to perform (add, subtract, multiply, divide)
            a: First operand
            b: Second operand

        Returns:
            Dictionary with result and operation details

        Raises:
            ValueError: If operation is invalid or division by zero
        """
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else None,
        }

        if operation not in operations:
            raise ValueError(f"Invalid operation: {operation}")

        result = operations[operation](a, b)

        if result is None:
            raise ValueError("Division by zero")

        return {
            "operation": operation,
            "operands": [a, b],
            "result": result
        }


class WeatherTool(Tool):
    """Example tool for retrieving weather information."""

    def get_definition(self) -> ToolDefinition:
        """Get weather tool definition.

        Returns:
            Tool definition for weather lookup
        """
        return ToolDefinition(
            name="get_weather",
            description="Get current weather information for a location",
            parameters={
                "location": {
                    "type": "string",
                    "description": "City name or location"
                }
            }
        )

    def execute(self, location: str) -> dict[str, Any]:
        """Execute weather lookup.

        NOTE: This is a mock implementation. In production, this would
        call a real weather API.

        Args:
            location: Location to get weather for

        Returns:
            Dictionary with weather information
        """
        # Mock weather data
        return {
            "location": location,
            "temperature": 72,
            "conditions": "Partly cloudy",
            "humidity": 65,
            "wind_speed": 10,
            "note": "This is mock data from the example tool"
        }
