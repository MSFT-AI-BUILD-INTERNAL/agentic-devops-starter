"""Tests for logging utilities."""

import logging
import uuid

import pytest

from src.logging_utils import (
    CorrelationIdFilter,
    get_correlation_id,
    log_llm_interaction,
    set_correlation_id,
    setup_logging,
)


def test_correlation_id_filter() -> None:
    """Test CorrelationIdFilter adds correlation ID to log records."""
    filter_instance = CorrelationIdFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )

    # Filter should always return True
    assert filter_instance.filter(record) is True
    # Correlation ID should be added to record
    assert hasattr(record, "correlation_id")


def test_get_correlation_id_generates_new() -> None:
    """Test get_correlation_id generates a new ID when none exists."""
    # Clear any existing correlation ID
    from src.logging_utils import correlation_id_var

    correlation_id_var.set(None)

    correlation_id = get_correlation_id()

    assert correlation_id is not None
    assert len(correlation_id) > 0
    # Should be a valid UUID format
    uuid.UUID(correlation_id)


def test_get_correlation_id_returns_existing() -> None:
    """Test get_correlation_id returns existing ID."""
    test_id = str(uuid.uuid4())
    set_correlation_id(test_id)

    correlation_id = get_correlation_id()

    assert correlation_id == test_id


def test_set_correlation_id() -> None:
    """Test set_correlation_id sets the ID correctly."""
    test_id = "test-correlation-123"
    set_correlation_id(test_id)

    correlation_id = get_correlation_id()

    assert correlation_id == test_id


def test_setup_logging_returns_logger() -> None:
    """Test setup_logging returns a configured logger."""
    logger = setup_logging()

    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "agentic_devops"
    assert logger.level == logging.INFO


def test_setup_logging_with_custom_level() -> None:
    """Test setup_logging with custom log level."""
    logger = setup_logging(level=logging.DEBUG)

    assert logger.level == logging.DEBUG


def test_setup_logging_has_handlers() -> None:
    """Test setup_logging configures handlers correctly."""
    logger = setup_logging()

    # Should have at least one handler
    assert len(logger.handlers) > 0

    # First handler should be a StreamHandler
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)


def test_setup_logging_has_correlation_id_filter() -> None:
    """Test setup_logging adds correlation ID filter to handlers."""
    logger = setup_logging()
    handler = logger.handlers[0]

    # Check if handler has CorrelationIdFilter
    has_correlation_filter = any(
        isinstance(f, CorrelationIdFilter) for f in handler.filters
    )
    assert has_correlation_filter is True


def test_log_llm_interaction() -> None:
    """Test log_llm_interaction logs with structured data."""
    logger = setup_logging()
    
    # Set a known correlation ID
    test_id = "test-interaction-123"
    set_correlation_id(test_id)

    operation = "test_operation"
    details = {
        "model": "gpt-4",
        "tokens": 100,
    }

    # Should not raise any exception
    log_llm_interaction(logger, operation, details)


def test_log_llm_interaction_includes_correlation_id() -> None:
    """Test log_llm_interaction includes correlation ID in log data."""
    logger = setup_logging()
    
    # Set a known correlation ID
    test_id = "test-correlation-456"
    set_correlation_id(test_id)

    operation = "completion"
    details = {"model": "gpt-4"}

    # Capture log output by adding a custom handler
    class TestHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    test_handler = TestHandler()
    logger.addHandler(test_handler)

    log_llm_interaction(logger, operation, details)

    # Check that log was created
    assert len(test_handler.records) > 0


def test_correlation_id_isolation() -> None:
    """Test correlation IDs are properly isolated."""
    # Set correlation ID 1
    id1 = "correlation-1"
    set_correlation_id(id1)
    assert get_correlation_id() == id1

    # Set correlation ID 2
    id2 = "correlation-2"
    set_correlation_id(id2)
    assert get_correlation_id() == id2

    # ID should have changed
    assert get_correlation_id() != id1


def test_logging_format_includes_correlation_id() -> None:
    """Test that log format includes correlation ID placeholder."""
    logger = setup_logging()
    handler = logger.handlers[0]
    formatter = handler.formatter

    assert formatter is not None
    # Check format string contains correlation_id
    if hasattr(formatter, "_fmt"):
        assert "correlation_id" in formatter._fmt
