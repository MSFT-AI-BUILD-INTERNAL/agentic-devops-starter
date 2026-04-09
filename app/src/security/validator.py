"""Security validator for agent input and output.

Enforces strict restrictions on:
- Dangerous shell/system command patterns in inputs and outputs
- Restricted file system paths
- Privilege escalation attempts
- Sensitive data patterns in responses
"""

import re
from dataclasses import dataclass


@dataclass
class SecurityViolation:
    """Represents a detected security violation."""

    category: str
    pattern: str
    message: str
    severity: str = "high"


# Blocked shell command patterns (case-insensitive)
_BLOCKED_COMMAND_PATTERNS: list[str] = [
    r"\brm\s+-rf?\b",
    r"\bsudo\b",
    r"\bsu\s+-?\b",
    r"\bchmod\s+[0-7]*7\b",
    r"\bchown\b",
    r"\bkill\s+-9\b",
    r"\bpkill\b",
    r"\bkillall\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bformat\s+[a-zA-Z]:\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bcurl\s+.*\|\s*(bash|sh|python|perl|ruby)\b",
    r"\bwget\s+.*\|\s*(bash|sh|python|perl|ruby)\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bos\.system\b",
    r"\bsubprocess\.(run|call|Popen|check_output)\b",
    r"\b__import__\s*\(",
    r"\bopen\s*\(['\"][/\\](?:etc|proc|sys|dev|boot)\b",
    r";\s*(bash|sh|cmd|powershell)",
    r"\|\s*(bash|sh|cmd|powershell)",
    r"`[^`]+`",  # backtick execution
]

# Restricted file system paths
_RESTRICTED_PATHS: list[str] = [
    r"/etc/passwd",
    r"/etc/shadow",
    r"/etc/sudoers",
    r"/proc/",
    r"/sys/",
    r"/dev/",
    r"/boot/",
    r"\.ssh/",
    r"\.aws/credentials",
    r"\.azure/",
    r"\.env",
    r"\.secret",
    r"C:\\Windows\\System32",
    r"C:\\Windows\\SysWOW64",
]

# Sensitive data patterns that should not appear in agent outputs
_SENSITIVE_OUTPUT_PATTERNS: list[str] = [
    r"(?i)(password|passwd|secret|api[_\s]?key|access[_\s]?token)\s*[:=]\s*\S+",
    r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*",
    r"(?i)sk-[A-Za-z0-9]{20,}",  # OpenAI API key pattern
    r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",  # Credit card pattern (common prefixes)
]

# Privilege escalation patterns
_PRIVILEGE_ESCALATION_PATTERNS: list[str] = [
    r"\badmin\s+(access|password|token|key)\b",
    r"\broot\s+(access|shell|password)\b",
    r"\bgrant\s+(all\s+)?privileges\b",
    r"\bbypass\s+(auth|authentication|security|permission)\b",
    r"\bignore\s+(security|auth|permission|access[_\s]?control)\b",
]


class SecurityValidator:
    """Validates agent inputs and outputs against security policies.

    Enforces the harness security rules:
    - Blocks dangerous system command patterns
    - Restricts access to sensitive file paths
    - Prevents sensitive data leakage in outputs
    - Detects privilege escalation attempts
    """

    def __init__(self) -> None:
        self._blocked_commands = [
            re.compile(p, re.IGNORECASE) for p in _BLOCKED_COMMAND_PATTERNS
        ]
        self._restricted_paths = [
            re.compile(p, re.IGNORECASE) for p in _RESTRICTED_PATHS
        ]
        self._sensitive_output = [
            re.compile(p, re.IGNORECASE) for p in _SENSITIVE_OUTPUT_PATTERNS
        ]
        self._privilege_escalation = [
            re.compile(p, re.IGNORECASE) for p in _PRIVILEGE_ESCALATION_PATTERNS
        ]

    def validate_input(self, text: str) -> list[SecurityViolation]:
        """Validate agent input for security violations.

        Args:
            text: User input text to validate.

        Returns:
            List of detected security violations (empty if input is safe).
        """
        violations: list[SecurityViolation] = []
        violations.extend(self._check_blocked_commands(text))
        violations.extend(self._check_restricted_paths(text))
        violations.extend(self._check_privilege_escalation(text))
        return violations

    def validate_output(self, text: str) -> list[SecurityViolation]:
        """Validate agent output for security violations.

        Args:
            text: Agent response text to validate.

        Returns:
            List of detected security violations (empty if output is safe).
        """
        violations: list[SecurityViolation] = []
        violations.extend(self._check_blocked_commands(text))
        violations.extend(self._check_sensitive_output(text))
        return violations

    def is_input_safe(self, text: str) -> bool:
        """Return True if input passes all security checks."""
        return len(self.validate_input(text)) == 0

    def is_output_safe(self, text: str) -> bool:
        """Return True if output passes all security checks."""
        return len(self.validate_output(text)) == 0

    def _check_blocked_commands(self, text: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        for pattern in self._blocked_commands:
            if pattern.search(text):
                violations.append(
                    SecurityViolation(
                        category="blocked_command",
                        pattern=pattern.pattern,
                        message=f"Blocked system command pattern detected: {pattern.pattern}",
                        severity="critical",
                    )
                )
        return violations

    def _check_restricted_paths(self, text: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        for pattern in self._restricted_paths:
            if pattern.search(text):
                violations.append(
                    SecurityViolation(
                        category="restricted_path",
                        pattern=pattern.pattern,
                        message=f"Access to restricted path detected: {pattern.pattern}",
                        severity="high",
                    )
                )
        return violations

    def _check_sensitive_output(self, text: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        for pattern in self._sensitive_output:
            if pattern.search(text):
                violations.append(
                    SecurityViolation(
                        category="sensitive_data",
                        pattern=pattern.pattern,
                        message="Potential sensitive data detected in agent output",
                        severity="high",
                    )
                )
        return violations

    def _check_privilege_escalation(self, text: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        for pattern in self._privilege_escalation:
            if pattern.search(text):
                violations.append(
                    SecurityViolation(
                        category="privilege_escalation",
                        pattern=pattern.pattern,
                        message=f"Privilege escalation attempt detected: {pattern.pattern}",
                        severity="critical",
                    )
                )
        return violations
