"""Post-execution harness compliance hook.

After each agent action the hook inspects the agent's input, output, and
state to determine whether the harness rules were violated.  Violations are
logged and, when the *fail_on_violation* flag is set, a ``HarnessViolationError``
is raised so the caller can decide how to handle enforcement.
"""

import logging
from dataclasses import dataclass, field

from ..security.validator import SecurityValidator, SecurityViolation

logger = logging.getLogger("agentic_devops")


@dataclass
class HarnessViolationReport:
    """Summary of harness compliance check results."""

    input_violations: list[SecurityViolation] = field(default_factory=list)
    output_violations: list[SecurityViolation] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        """True when at least one violation was detected."""
        return bool(self.input_violations or self.output_violations)

    @property
    def all_violations(self) -> list[SecurityViolation]:
        """All violations across input and output."""
        return self.input_violations + self.output_violations

    @property
    def critical_violations(self) -> list[SecurityViolation]:
        """Only violations with ``severity='critical'``."""
        return [v for v in self.all_violations if v.severity == "critical"]


class HarnessViolationError(RuntimeError):
    """Raised when a critical harness violation is detected and enforcement is enabled."""

    def __init__(self, report: HarnessViolationReport) -> None:
        messages = [v.message for v in report.critical_violations]
        super().__init__("Harness violation(s) detected: " + "; ".join(messages))
        self.report = report


class HarnessHook:
    """Post-execution hook that validates agent input/output against harness rules.

    The hook is called after every agent message processing cycle.  It uses
    :class:`~src.security.validator.SecurityValidator` to detect violations and
    either logs them (``fail_on_violation=False``) or raises
    :class:`HarnessViolationError` (``fail_on_violation=True``).

    Usage::

        hook = HarnessHook(fail_on_violation=True)
        report = hook.run(user_input="...", agent_output="...")
        if report.has_violations:
            ...
    """

    def __init__(self, fail_on_violation: bool = False) -> None:
        """Create a HarnessHook.

        Args:
            fail_on_violation: When ``True``, raises :class:`HarnessViolationError`
                for critical violations.  When ``False`` (default), violations are
                logged but execution continues.
        """
        self._validator = SecurityValidator()
        self._fail_on_violation = fail_on_violation

    def run(self, user_input: str, agent_output: str) -> HarnessViolationReport:
        """Run the harness compliance check.

        Args:
            user_input: The original user message.
            agent_output: The agent's response.

        Returns:
            :class:`HarnessViolationReport` describing any violations found.

        Raises:
            HarnessViolationError: If *fail_on_violation* is ``True`` and at
                least one **critical** violation is detected.
        """
        report = HarnessViolationReport(
            input_violations=self._validator.validate_input(user_input),
            output_violations=self._validator.validate_output(agent_output),
        )

        if report.has_violations:
            self._log_violations(report)
            if self._fail_on_violation and report.critical_violations:
                raise HarnessViolationError(report)

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_violations(self, report: HarnessViolationReport) -> None:
        for violation in report.input_violations:
            logger.warning(
                "Harness input violation [%s/%s]: %s",
                violation.category,
                violation.severity,
                violation.message,
            )
        for violation in report.output_violations:
            logger.warning(
                "Harness output violation [%s/%s]: %s",
                violation.category,
                violation.severity,
                violation.message,
            )
