"""Tests for agent tools."""

import pytest

from src.agents.tools import CalculatorTool, WeatherTool


def test_calculator_tool_definition() -> None:
    """Test calculator tool definition."""
    tool = CalculatorTool()
    definition = tool.get_definition()

    assert definition.name == "calculator"
    assert "arithmetic" in definition.description.lower()
    assert "operation" in definition.parameters
    assert "a" in definition.parameters
    assert "b" in definition.parameters


def test_calculator_add() -> None:
    """Test calculator addition."""
    tool = CalculatorTool()
    result = tool.execute(operation="add", a=5, b=3)

    assert result["operation"] == "add"
    assert result["result"] == 8
    assert result["operands"] == [5, 3]


def test_calculator_subtract() -> None:
    """Test calculator subtraction."""
    tool = CalculatorTool()
    result = tool.execute(operation="subtract", a=10, b=4)

    assert result["operation"] == "subtract"
    assert result["result"] == 6


def test_calculator_multiply() -> None:
    """Test calculator multiplication."""
    tool = CalculatorTool()
    result = tool.execute(operation="multiply", a=7, b=6)

    assert result["operation"] == "multiply"
    assert result["result"] == 42


def test_calculator_divide() -> None:
    """Test calculator division."""
    tool = CalculatorTool()
    result = tool.execute(operation="divide", a=20, b=4)

    assert result["operation"] == "divide"
    assert result["result"] == 5


def test_calculator_divide_by_zero() -> None:
    """Test calculator division by zero error."""
    tool = CalculatorTool()

    with pytest.raises(ValueError, match="Division by zero"):
        tool.execute(operation="divide", a=10, b=0)


def test_calculator_invalid_operation() -> None:
    """Test calculator with invalid operation."""
    tool = CalculatorTool()

    with pytest.raises(ValueError, match="Invalid operation"):
        tool.execute(operation="power", a=2, b=3)


def test_weather_tool_definition() -> None:
    """Test weather tool definition."""
    tool = WeatherTool()
    definition = tool.get_definition()

    assert definition.name == "get_weather"
    assert "weather" in definition.description.lower()
    assert "location" in definition.parameters


def test_weather_tool_execute() -> None:
    """Test weather tool execution."""
    tool = WeatherTool()
    result = tool.execute(location="Seattle")

    assert result["location"] == "Seattle"
    assert "temperature" in result
    assert "conditions" in result


def test_weather_tool_different_locations() -> None:
    """Test weather tool with different locations."""
    tool = WeatherTool()

    result1 = tool.execute(location="New York")
    assert result1["location"] == "New York"

    result2 = tool.execute(location="London")
    assert result2["location"] == "London"
