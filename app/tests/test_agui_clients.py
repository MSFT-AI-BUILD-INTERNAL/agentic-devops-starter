"""Tests for the AG-UI client tools.

Tests client-side tool logic (get_weather) defined in agui_client.py.
"""


def test_get_weather_known_locations() -> None:
    """Test get_weather returns correct data for known locations."""
    from agui_client import get_weather

    # @ai_function wraps sync tools; the return value is always str at runtime.
    for location, expected in [
        ("Seattle", "Rainy"),
        ("San Francisco", "Foggy"),
        ("New York", "Sunny"),
        ("London", "Cloudy"),
        ("Tokyo", "Clear"),
        ("Sydney", "Sunny"),
    ]:
        result = get_weather(location)
        assert isinstance(result, str), f"get_weather({location!r}) did not return str"
        assert expected in result, f"Expected {expected!r} in get_weather({location!r}), got {result!r}"


def test_get_weather_case_insensitive() -> None:
    """Test get_weather is case-insensitive."""
    from agui_client import get_weather

    assert get_weather("Seattle") == get_weather("SEATTLE")
    assert get_weather("Seattle") == get_weather("seattle")


def test_get_weather_unknown_location() -> None:
    """Test get_weather returns fallback for unknown location."""
    from agui_client import get_weather

    result = get_weather("Unknown City")
    assert isinstance(result, str)
    assert "not available" in result
    assert "Unknown City" in result


def test_get_weather_return_type() -> None:
    """Test get_weather returns a string."""
    from agui_client import get_weather

    result = get_weather("Seattle")
    assert isinstance(result, str)


def test_agui_client_exports() -> None:
    """Test that agui_client exposes expected public API."""
    import agui_client

    assert callable(agui_client.main)
    assert callable(agui_client.get_weather)
