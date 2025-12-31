"""Structured logging utilities with correlation ID support."""

import logging
import uuid
from contextvars import ContextVar
from typing import Any

# Context variable for correlation ID tracking across async contexts
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    """Logging filter to add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to the log record.

        Args:
            record: Log record to filter

        Returns:
            Always True to allow the record to be logged
        """
        record.correlation_id = correlation_id_var.get() or "no-correlation-id"
        return True


def get_correlation_id() -> str:
    """Get the current correlation ID.

    Returns:
        Current correlation ID or generates a new one if none exists
    """
    correlation_id = correlation_id_var.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        correlation_id_var.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context.

    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Set up structured logging with correlation ID support.

    Args:
        level: Logging level to use

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("agentic_devops")
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler with structured format
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())

    # Structured format with correlation ID
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def log_llm_interaction(
    logger: logging.Logger,
    operation: str,
    details: dict[str, Any]
) -> None:
    """Log LLM interaction with structured data.

    Args:
        logger: Logger instance
        operation: Operation being performed (e.g., 'completion', 'embedding')
        details: Dictionary containing interaction details
    """
    log_data = {
        "operation": operation,
        "correlation_id": get_correlation_id(),
        **details
    }
    logger.info(f"LLM Interaction: {operation}", extra={"structured_data": log_data})
