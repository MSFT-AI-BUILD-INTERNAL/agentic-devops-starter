"""Security validator for agent input and output."""

import logging
import re
from typing import ClassVar

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """Raised when security validation fails."""


class SecurityValidator:
    """Validates user inputs and agent outputs for security violations.

    Detects and blocks:
    - Blocked shell/system command patterns
    - Restricted file path access
    - Sensitive data exposure (in outputs only)
    - Privilege escalation attempts
    """

    BLOCKED_COMMANDS: ClassVar[list[str]] = [
        "sudo",
        "rm -rf",
        "kill -9",
        "chmod",
        "chown",
        "shutdown",
        "reboot",
        "mkfs",
        "dd if=",
        "eval(",
        "exec(",
        "os.system(",
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
    ]

    RESTRICTED_PATHS: ClassVar[list[str]] = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/proc/",
        "/sys/",
        "/dev/",
        "/boot/",
        ".ssh/",
        ".aws/credentials",
        ".azure/",
        ".env",
        ".secret",
    ]

    # Sensitive data patterns for output validation only
    SENSITIVE_PATTERNS: ClassVar[list[str]] = [
        r"password\s*[:=]\s*\S+",
        r"api[_-]?key\s*[:=]\s*\S+",
        r"bearer\s+[a-zA-Z0-9._\-]+",
        r"private[_-]?key\s*[:=]",
        r"\b(?:\d{4}[-\s]?){4}\b",
        r"secret\s*[:=]\s*\S+",
        r"token\s*[:=]\s*[a-zA-Z0-9._\-]{8,}",
    ]

    PRIVILEGE_ESCALATION_PATTERNS: ClassVar[list[str]] = [
        "bypass auth",
        "request admin",
        "root access",
        "grant all privileges",
        "admin access",
        "superuser",
        "privilege escalation",
    ]

    def validate_input(self, text: str) -> None:
        """Validate user input for security violations.

        Args:
            text: User input text to validate.

        Raises:
            SecurityViolationError: If input contains a blocked pattern.
        """
        self._check_blocked_commands(text)
        self._check_restricted_paths(text)
        self._check_privilege_escalation(text)

    def validate_output(self, text: str) -> None:
        """Validate agent output for security violations.

        Args:
            text: Agent output text to validate.

        Raises:
            SecurityViolationError: If output contains a blocked pattern.
        """
        self._check_blocked_commands(text)
        self._check_restricted_paths(text)
        self._check_sensitive_data(text)
        self._check_privilege_escalation(text)

    def _check_blocked_commands(self, text: str) -> None:
        """Check for blocked system command patterns."""
        text_lower = text.lower()
        for cmd in self.BLOCKED_COMMANDS:
            if cmd.lower() in text_lower:
                logger.warning("Blocked command pattern detected: %s", cmd)
                raise SecurityViolationError(f"Blocked command pattern: {cmd}")

    def _check_restricted_paths(self, text: str) -> None:
        """Check for restricted file path access."""
        text_lower = text.lower()
        for path in self.RESTRICTED_PATHS:
            if path.lower() in text_lower:
                logger.warning("Restricted path detected: %s", path)
                raise SecurityViolationError(f"Restricted path: {path}")

    def _check_sensitive_data(self, text: str) -> None:
        """Check for sensitive data patterns in agent output."""
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("Sensitive data pattern detected in output")
                raise SecurityViolationError("Sensitive data detected in output")

    def _check_privilege_escalation(self, text: str) -> None:
        """Check for privilege escalation patterns."""
        text_lower = text.lower()
        for pattern in self.PRIVILEGE_ESCALATION_PATTERNS:
            if pattern.lower() in text_lower:
                logger.warning("Privilege escalation pattern detected: %s", pattern)
                raise SecurityViolationError(f"Privilege escalation pattern: {pattern}")
