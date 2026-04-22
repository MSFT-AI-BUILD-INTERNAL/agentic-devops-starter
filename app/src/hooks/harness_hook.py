"""Harness hook for post-execution compliance validation."""

import logging
from dataclasses import dataclass, field

from ..security.validator import SecurityValidator, SecurityViolationError

logger = logging.getLogger(__name__)


class HarnessViolationError(Exception):
    """Raised when a harness violation is detected in enforce mode."""


@dataclass
class HarnessReport:
    """Result of a harness hook execution."""

    passed: bool
    violations: list[str] = field(default_factory=list)
    user_input: str = ""
    agent_output: str = ""

    @property
    def violation_count(self) -> int:
        """Number of violations detected."""
        return len(self.violations)

    @property
    def has_violations(self) -> bool:
        """Whether any violations were detected."""
        return len(self.violations) > 0


class HarnessHook:
    """Post-execution harness compliance validator.

    Validates agent input and output against harness rules after each
    ``process_message()`` cycle.

    Args:
        fail_on_violation: When ``True``, raises ``HarnessViolationError``
            on violations (enforce mode). When ``False`` (default), logs the
            violation and continues (observe mode).

    Enforcement modes:

    - **Observe** (default, ``fail_on_violation=False``): Development / staging.
    - **Enforce** (``fail_on_violation=True``): Production / high-security contexts.
    """

    def __init__(self, fail_on_violation: bool = False) -> None:
        self.fail_on_violation = fail_on_violation
        self._validator = SecurityValidator()

    def run(self, user_input: str, agent_output: str) -> HarnessReport:
        """Run harness validation after an agent cycle.

        Args:
            user_input: The original user message.
            agent_output: The agent's response.

        Returns:
            A ``HarnessReport`` describing the outcome.

        Raises:
            HarnessViolationError: If *fail_on_violation* is ``True`` and a
                violation is detected.
        """
        violations: list[str] = []

        for text, label, check_fn in (
            (user_input, "input", self._validator.validate_input),
            (agent_output, "output", self._validator.validate_output),
        ):
            try:
                check_fn(text)
            except SecurityViolationError as exc:
                msg = f"{label} violation: {exc}"
                violations.append(msg)
                logger.warning("HarnessHook violation detected — %s", msg)

        report = HarnessReport(
            passed=len(violations) == 0,
            violations=violations,
            user_input=user_input,
            agent_output=agent_output,
        )

        if report.has_violations and self.fail_on_violation:
            raise HarnessViolationError("; ".join(violations))

        return report
