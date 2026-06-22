"""Token usage optimisation utilities for GitHub Copilot SDK sessions.

Usage
-----
Call :func:`truncate_context` on any context string before passing it to an
agent session.  When the feature flag is **off** (default) the function is a
no-op and returns the original string unchanged, so existing behaviour is fully
preserved.  When the flag is **on** the tail of the string (most-recent content)
is kept up to the configured character limit.

Feature flag
------------
``COPILOT_API_TOKEN_OPTIMIZATION_ENABLED=true``   — enable truncation
``COPILOT_API_TOKEN_OPTIMIZATION_MAX_CONTEXT_CHARS=8000`` — character budget
"""

from src.config import settings


def truncate_context(context: str) -> str:
    """Return *context*, truncated when the token optimisation flag is on.

    When disabled (default), returns *context* unchanged.
    When enabled, keeps the **trailing** portion up to
    ``settings.token_optimization_max_context_chars`` characters so that the
    most-recent agent output is always preserved.
    """
    if not settings.token_optimization_enabled:
        return context

    max_chars = settings.token_optimization_max_context_chars
    if len(context) <= max_chars:
        return context

    return context[-max_chars:]
