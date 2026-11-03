#!/bin/sh
set -eu

if [ -z "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" ]; then
  echo "APPLICATIONINSIGHTS_CONNECTION_STRING not set; OTLP forwarder disabled."
  exec sleep infinity
fi

exec /app/.venv/bin/python /app/otlp_forwarder.py
