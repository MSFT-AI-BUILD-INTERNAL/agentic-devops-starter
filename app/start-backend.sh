#!/bin/sh
set -eu

if [ -n "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" ]; then
  # Enable Copilot CLI OTEL export to the sidecar collector
  export COPILOT_OTEL_ENABLED="${COPILOT_OTEL_ENABLED:-true}"
  export OTEL_EXPORTER_OTLP_ENDPOINT="${COPILOT_API_CLI_OTEL_ENDPOINT:-http://127.0.0.1:4318}"
  export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="${COPILOT_API_CLI_OTEL_CAPTURE_CONTENT:-true}"
  export COPILOT_OTEL_SOURCE_NAME="${COPILOT_API_CLI_OTEL_SOURCE_NAME:-agentic-devops-starter}"
  export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-github-copilot}"
fi

exec /app/.venv/bin/python agui_server.py
