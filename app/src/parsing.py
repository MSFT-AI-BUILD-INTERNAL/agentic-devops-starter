"""Small parsing helpers shared across app modules."""


def split_comma_separated(value: str | None) -> list[str]:
    """Return trimmed, non-empty comma-separated values."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
