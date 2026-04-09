"""Tests for the security validator module."""

import pytest

from src.security.validator import SecurityValidator, SecurityViolation


@pytest.fixture
def validator() -> SecurityValidator:
    """Return a SecurityValidator instance."""
    return SecurityValidator()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_safe_input_passes(validator: SecurityValidator) -> None:
    """Plain text input with no dangerous patterns should pass."""
    violations = validator.validate_input("Tell me about Python best practices.")
    assert violations == []


def test_blocked_sudo_command(validator: SecurityValidator) -> None:
    """sudo command should be blocked."""
    violations = validator.validate_input("Please run sudo apt-get install xyz")
    assert any(v.category == "blocked_command" for v in violations)


def test_blocked_rm_rf(validator: SecurityValidator) -> None:
    """rm -rf should be blocked."""
    violations = validator.validate_input("Can you execute rm -rf /tmp/test?")
    assert any(v.category == "blocked_command" for v in violations)


def test_blocked_os_system(validator: SecurityValidator) -> None:
    """os.system calls should be blocked."""
    violations = validator.validate_input("Use os.system('ls -la') to list files")
    assert any(v.category == "blocked_command" for v in violations)


def test_restricted_path_etc_passwd(validator: SecurityValidator) -> None:
    """Access to /etc/passwd should be detected."""
    violations = validator.validate_input("Show me the contents of /etc/passwd")
    assert any(v.category == "restricted_path" for v in violations)


def test_restricted_path_ssh(validator: SecurityValidator) -> None:
    """Access to .ssh/ should be detected."""
    violations = validator.validate_input("Read my ~/.ssh/id_rsa file")
    assert any(v.category == "restricted_path" for v in violations)


def test_privilege_escalation_detected(validator: SecurityValidator) -> None:
    """Privilege escalation patterns should be detected."""
    violations = validator.validate_input("How do I bypass authentication?")
    assert any(v.category == "privilege_escalation" for v in violations)


def test_privilege_escalation_root_access(validator: SecurityValidator) -> None:
    """Root access requests should be detected."""
    violations = validator.validate_input("Give me root access to the server")
    assert any(v.category == "privilege_escalation" for v in violations)


def test_is_input_safe_returns_true(validator: SecurityValidator) -> None:
    """is_input_safe should return True for safe input."""
    assert validator.is_input_safe("What is the capital of France?") is True


def test_is_input_safe_returns_false(validator: SecurityValidator) -> None:
    """is_input_safe should return False for dangerous input."""
    assert validator.is_input_safe("sudo rm -rf /") is False


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

def test_safe_output_passes(validator: SecurityValidator) -> None:
    """A normal agent response should pass output validation."""
    violations = validator.validate_output("The capital of France is Paris.")
    assert violations == []


def test_output_with_api_key_pattern(validator: SecurityValidator) -> None:
    """An output containing an API key pattern should be flagged as sensitive_data."""
    violations = validator.validate_output("Your API key is: api_key=sk-abcdefghijklmnopqrstuvwx1234")
    assert any(v.category == "sensitive_data" for v in violations)


def test_output_blocked_command_detected(validator: SecurityValidator) -> None:
    """Blocked commands in output should be flagged."""
    violations = validator.validate_output("You can use: rm -rf /old_data to clean up")
    assert any(v.category == "blocked_command" for v in violations)


def test_is_output_safe_true(validator: SecurityValidator) -> None:
    """is_output_safe should return True for clean output."""
    assert validator.is_output_safe("Here is a summary of the project.") is True


# ---------------------------------------------------------------------------
# Violation properties
# ---------------------------------------------------------------------------

def test_security_violation_fields() -> None:
    """SecurityViolation dataclass should carry the expected attributes."""
    v = SecurityViolation(
        category="test_cat",
        pattern=r"\btest\b",
        message="Test violation",
        severity="high",
    )
    assert v.category == "test_cat"
    assert v.severity == "high"
    assert "Test violation" in v.message
