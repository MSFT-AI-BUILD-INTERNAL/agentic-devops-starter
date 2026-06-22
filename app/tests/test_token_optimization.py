"""Tests for token_optimization module."""

import pytest

from src import token_optimization
from src.token_optimization import truncate_context

# ---------------------------------------------------------------------------
# Feature flag OFF (default) — no-op behaviour
# ---------------------------------------------------------------------------


def test_truncate_context_disabled_returns_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """truncate_context is a no-op when the feature flag is off."""
    monkeypatch.setattr(token_optimization.settings, "token_optimization_enabled", False)
    long_context = "x" * 20_000
    assert truncate_context(long_context) == long_context


def test_truncate_context_disabled_empty_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_optimization.settings, "token_optimization_enabled", False)
    assert truncate_context("") == ""


# ---------------------------------------------------------------------------
# Feature flag ON — truncation behaviour
# ---------------------------------------------------------------------------


def test_truncate_context_enabled_short_context_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context shorter than the limit is returned unchanged."""
    monkeypatch.setattr(token_optimization.settings, "token_optimization_enabled", True)
    monkeypatch.setattr(token_optimization.settings, "token_optimization_max_context_chars", 100)
    short = "hello"
    assert truncate_context(short) == short


def test_truncate_context_enabled_exact_limit_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context exactly at the limit is returned unchanged."""
    monkeypatch.setattr(token_optimization.settings, "token_optimization_enabled", True)
    monkeypatch.setattr(token_optimization.settings, "token_optimization_max_context_chars", 10)
    exactly = "a" * 10
    assert truncate_context(exactly) == exactly


def test_truncate_context_enabled_over_limit_keeps_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context over the limit is truncated, keeping the most-recent (tail) content."""
    monkeypatch.setattr(token_optimization.settings, "token_optimization_enabled", True)
    monkeypatch.setattr(token_optimization.settings, "token_optimization_max_context_chars", 5)
    result = truncate_context("old_content_recent")
    assert result == "ecent"
    assert len(result) == 5


def test_truncate_context_enabled_tail_is_most_recent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The kept portion is the last N chars (most-recent agent output)."""
    monkeypatch.setattr(token_optimization.settings, "token_optimization_enabled", True)
    monkeypatch.setattr(token_optimization.settings, "token_optimization_max_context_chars", 20)
    recent = "RECENT_CONTENT_HERE!"
    context = ("a" * 200) + recent
    result = truncate_context(context)
    assert result.endswith(recent)
    assert len(result) == 20
