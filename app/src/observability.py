"""OpenTelemetry observability setup for Azure Monitor.

Configures OpenTelemetry exporters that send traces, logs, and metrics to
Azure Application Insights.

This module is a no-op when ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is not
set, so local development keeps working without any tracing configuration.

Required environment variables (see ``.env.example``):

* ``APPLICATIONINSIGHTS_CONNECTION_STRING`` -- Connection string of the
  Application Insights resource. Without this value tracing is disabled.

Optional environment variables:

* ``OTEL_SERVICE_NAME`` -- Service name reported on every span. Defaults to
  ``agentic-devops-starter``.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Module-level guard so configure_observability() is idempotent across
# create_app() calls (e.g. in tests that build the app multiple times).
_CONFIGURED = False


def configure_observability() -> bool:
    """Configure Azure Monitor OpenTelemetry exporters.

    Returns ``True`` if observability was configured (or was already configured
    on a previous call), ``False`` if it was skipped because the Application
    Insights connection string is not set.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return True

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        logger.info(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set; tracing disabled (local dev mode)."
        )
        return False

    # Default a service name so spans are easy to find in App Insights.
    os.environ.setdefault("OTEL_SERVICE_NAME", "agentic-devops-starter")

    # Imported lazily so the package is only required when tracing is enabled.
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=connection_string)

    _CONFIGURED = True
    logger.info(
        "Azure Monitor tracing enabled: service=%s",
        os.environ["OTEL_SERVICE_NAME"],
    )
    return True
