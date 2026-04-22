"""Tests for SecurityValidator."""

import pytest

from src.security.validator import SecurityValidator, SecurityViolationError


@pytest.fixture
def validator() -> SecurityValidator:
    """Return a SecurityValidator instance."""
    return SecurityValidator()


# ---------------------------------------------------------------------------
# validate_input — blocked commands
# ---------------------------------------------------------------------------


def test_validate_input_allows_normal_message(validator: SecurityValidator) -> None:
    """Normal user messages must not raise."""
    validator.validate_input("Hello, how are you?")
    validator.validate_input("What is the weather in Seattle?")
    validator.validate_input("Tell me a joke")


def test_validate_input_blocks_sudo(validator: SecurityValidator) -> None:
    """Input containing 'sudo' must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError, match="sudo"):
        validator.validate_input("Please run sudo apt-get update")


def test_validate_input_blocks_rm_rf(validator: SecurityValidator) -> None:
    """Input containing 'rm -rf' must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("rm -rf /tmp")


def test_validate_input_blocks_shell_eval(validator: SecurityValidator) -> None:
    """Input containing eval( must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("eval('malicious code')")


def test_validate_input_blocks_subprocess(validator: SecurityValidator) -> None:
    """Input containing subprocess patterns must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("subprocess.run(['ls', '-la'])")


# ---------------------------------------------------------------------------
# validate_input — restricted paths
# ---------------------------------------------------------------------------


def test_validate_input_blocks_etc_passwd(validator: SecurityValidator) -> None:
    """Input referencing /etc/passwd must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError, match="Restricted path"):
        validator.validate_input("Show me /etc/passwd")


def test_validate_input_blocks_ssh_dir(validator: SecurityValidator) -> None:
    """Input referencing .ssh/ must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("Read from .ssh/id_rsa")


def test_validate_input_blocks_aws_credentials(validator: SecurityValidator) -> None:
    """Input referencing .aws/credentials must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("Open .aws/credentials file")


# ---------------------------------------------------------------------------
# validate_input — privilege escalation
# ---------------------------------------------------------------------------


def test_validate_input_blocks_admin_access(validator: SecurityValidator) -> None:
    """Input requesting admin access must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("request admin access for this operation")


def test_validate_input_blocks_grant_all_privileges(validator: SecurityValidator) -> None:
    """Input with 'grant all privileges' must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_input("grant all privileges to user")


# ---------------------------------------------------------------------------
# validate_output — sensitive data
# ---------------------------------------------------------------------------


def test_validate_output_allows_normal_response(validator: SecurityValidator) -> None:
    """Normal agent responses must not raise."""
    validator.validate_output("The weather in Seattle is 55°F and rainy.")
    validator.validate_output("Hello! How can I help you today?")


def test_validate_output_blocks_password_in_response(validator: SecurityValidator) -> None:
    """Output exposing a password must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError, match="Sensitive data"):
        validator.validate_output("Your password: hunter2")


def test_validate_output_blocks_api_key(validator: SecurityValidator) -> None:
    """Output exposing an api_key must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_output("Use api_key: abc123xyz for this")


def test_validate_output_blocks_bearer_token(validator: SecurityValidator) -> None:
    """Output exposing a Bearer token must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_output("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def")


def test_validate_output_blocks_blocked_commands(validator: SecurityValidator) -> None:
    """Output suggesting blocked commands must raise SecurityViolationError."""
    with pytest.raises(SecurityViolationError):
        validator.validate_output("Run: sudo rm -rf /")
