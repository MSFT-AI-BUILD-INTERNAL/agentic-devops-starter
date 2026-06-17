#!/bin/sh
set -eu

if [ -n "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" ]; then
  # Enable Copilot CLI OTEL export to the sidecar collector
  export COPILOT_API_CLI_OTEL_ENDPOINT="${COPILOT_API_CLI_OTEL_ENDPOINT:-http://127.0.0.1:4318}"
  export COPILOT_API_CLI_OTEL_CAPTURE_CONTENT="${COPILOT_API_CLI_OTEL_CAPTURE_CONTENT:-true}"
fi

exec /app/.venv/bin/python agui_server.py
