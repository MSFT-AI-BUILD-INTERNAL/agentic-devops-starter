"""Structured logging setup with correlation ID support."""

import logging
import sys
import uuid
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationFilter(logging.Filter):
    """Inject correlation_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id.get("")  # type: ignore[attr-defined]
        return True


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("copilot_api")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(correlation_id)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)

    return logger


def new_correlation_id() -> str:
    """Generate and set a new correlation ID, returning it."""
    cid = uuid.uuid4().hex[:12]
    correlation_id.set(cid)
    return cid
