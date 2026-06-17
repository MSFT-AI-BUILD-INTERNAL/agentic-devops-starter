#!/bin/sh
set -eu

if [ -n "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" ] && [ -z "${COPILOT_API_CLI_OTEL_ENDPOINT:-}" ]; then
  export COPILOT_API_CLI_OTEL_ENDPOINT="http://127.0.0.1:4318"
fi

exec /app/.venv/bin/python agui_server.py
