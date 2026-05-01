"""OpenTelemetry observability setup for Microsoft Foundry / Azure Monitor.

Configures OpenTelemetry exporters that send traces, logs, and metrics to the
Azure Application Insights resource attached to a Microsoft Foundry (Azure AI
Foundry) project. It also enables ``agent_framework`` instrumentation so that
``ChatAgent`` runs and tool calls produce GenAI semantic-convention spans.

This module is a no-op when ``APPLICATIONINSIGHTS_CONNECTION_STRING`` is not
set, so local development keeps working without any tracing configuration.

Required environment variables (see ``.env.example``):

* ``APPLICATIONINSIGHTS_CONNECTION_STRING`` -- Connection string of the
  Application Insights resource linked to your Foundry project. Without this
  value tracing is disabled.

Optional environment variables:

* ``OTEL_SERVICE_NAME`` -- Service name reported on every span. Defaults to
  ``agentic-devops-starter``.
* ``ENABLE_SENSITIVE_DATA`` -- Set to ``true`` to include prompt / completion
  contents on agent spans. Off by default; only enable in non-production
  environments.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Module-level guard so configure_observability() is idempotent across
# create_app() calls (e.g. in tests that build the app multiple times).
_CONFIGURED = False


def configure_observability() -> bool:
    """Configure Azure Monitor OpenTelemetry exporters and agent instrumentation.

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
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set; "
            "Foundry tracing disabled (local dev mode)."
        )
        return False

    # Default a service name so spans are easy to find in Foundry / App Insights.
    os.environ.setdefault("OTEL_SERVICE_NAME", "agentic-devops-starter")

    # Imported lazily so the package is only required when tracing is enabled.
    from agent_framework.observability import enable_instrumentation
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=connection_string)

    # Turn on agent_framework's GenAI spans (ChatAgent runs, tool invocations).
    enable_sensitive = os.environ.get("ENABLE_SENSITIVE_DATA", "").lower() in {
        "1",
        "true",
        "yes",
    }
    enable_instrumentation(enable_sensitive_data=enable_sensitive)

    _CONFIGURED = True
    logger.info(
        "Foundry tracing enabled: service=%s, sensitive_data=%s",
        os.environ["OTEL_SERVICE_NAME"],
        enable_sensitive,
    )
    return True
