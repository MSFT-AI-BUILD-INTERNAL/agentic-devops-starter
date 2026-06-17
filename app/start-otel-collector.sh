#!/bin/sh
set -eu

if [ -z "${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" ]; then
  echo "APPLICATIONINSIGHTS_CONNECTION_STRING not set; OpenTelemetry Collector disabled."
  exec sleep infinity
fi

exec /usr/local/bin/otelcol-contrib --config=/app/otel-collector-config.yaml
