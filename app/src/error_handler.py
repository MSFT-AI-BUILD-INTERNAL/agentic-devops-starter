"""Centralized error handling and response building utilities."""

import logging
from typing import Any

from fastapi.responses import JSONResponse


def error_response(
    status_code: int, error_code: str, detail: str, extra_fields: dict[str, Any] | None = None
) -> JSONResponse:
    """Build a standardized error JSON response."""
    response_body: dict[str, Any] = {
        "error": error_code,
        "detail": detail,
    }
    if extra_fields:
        response_body.update(extra_fields)
    return JSONResponse(status_code=status_code, content=response_body)


def log_and_respond(
    logger: logging.Logger,
    status_code: int,
    error_code: str,
    detail: str,
    log_message: str,
    extra: dict[str, Any] | None = None,
    extra_fields: dict[str, Any] | None = None,
    exception: Exception | None = None,
) -> JSONResponse:
    """Log an error and return a JSON response.

    Args:
        logger: Logger instance
        status_code: HTTP status code
        error_code: Error code for client
        detail: Human-readable detail message
        log_message: Message to log
        extra: Extra context for logging
        extra_fields: Extra fields to include in JSON response
        exception: Exception to log (if any)
    """
    if exception:
        logger.exception(log_message, extra=extra or {})
    else:
        logger.warning(log_message, extra=extra or {})

    return error_response(status_code, error_code, detail, extra_fields)
