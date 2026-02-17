"""Tests for the AG-UI clients.

Tests the AG-UI client functionality including hybrid tool execution.
Follows all constitution requirements including type safety and test coverage.
"""

import pytest


def test_get_weather_tool() -> None:
    """Test the get_weather client-side tool."""
    from agui_client_hybrid import get_weather

    # Test known locations
    assert "Rainy" in get_weather("Seattle")
    assert "Foggy" in get_weather("San Francisco")
    assert "Sunny" in get_weather("New York")
    assert "Cloudy" in get_weather("London")

    # Test case insensitivity
    assert "Rainy" in get_weather("SEATTLE")
    assert "Rainy" in get_weather("seattle")

    # Test unknown location
    result = get_weather("Unknown City")
    assert "not available" in result


def test_weather_tool_type_annotations() -> None:
    """Test that the weather tool has proper return type."""
    from agui_client_hybrid import get_weather

    # The ai_function decorator wraps the function, so we check the actual callable
    result = get_weather("Seattle")
    assert isinstance(result, str)


def test_weather_tool_ai_function_decorator() -> None:
    """Test that the weather tool is an AIFunction."""
    from agent_framework._tools import AIFunction
    from agui_client_hybrid import get_weather

    # Check that the function is wrapped by ai_function decorator
    assert isinstance(get_weather, AIFunction)


@pytest.mark.asyncio
async def test_agui_client_import() -> None:
    """Test that the basic client can be imported."""
    import agui_client

    assert hasattr(agui_client, "main")


@pytest.mark.asyncio
async def test_agui_client_hybrid_import() -> None:
    """Test that the hybrid client can be imported."""
    import agui_client_hybrid

    assert hasattr(agui_client_hybrid, "main")
    assert hasattr(agui_client_hybrid, "run_demo_conversation")
    assert hasattr(agui_client_hybrid, "get_weather")
