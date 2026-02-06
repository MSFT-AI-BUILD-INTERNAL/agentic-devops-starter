"""Logging utilities with correlation ID support."""

import logging
import uuid
from contextvars import ContextVar
from typing import Any

# Context variable for correlation ID
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    """Adds correlation ID to log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "no-correlation-id"
        return True


def get_correlation_id() -> str:
    """Get or generate correlation ID."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup structured logging with correlation ID."""
    logger = logging.getLogger("agentic_devops")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger


def log_llm_interaction(logger: logging.Logger, operation: str, details: dict[str, Any]) -> None:
    """Log LLM interaction with structured data."""
    logger.info(f"LLM {operation}: {details}")
