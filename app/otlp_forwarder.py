#!/usr/bin/env python3
"""Minimal OTLP/HTTP forwarder sidecar: receives telemetry and forwards it to Azure Monitor.

Apps send OTLP/HTTP (protobuf) to http://127.0.0.1:4318/v1/{traces,logs,metrics}.
Authenticates with the App Service managed identity (falls back to IMDS on VMs).
"""
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("OTLP_FORWARDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("OTLP_FORWARDER_PORT", "4318"))
ENDPOINTS = {
    "/v1/traces": "https://managed-jinspark-insights-dce-4d93.eastus-1.ingest.monitor.azure.com/dataCollectionRules/dcr-cf52a36bb70546c69c09b3652b955588/streams/Microsoft-OTLP-Traces/otlp/v1/traces",
    "/v1/logs": "https://managed-jinspark-insights-dce-4d93.eastus-1.ingest.monitor.azure.com/dataCollectionRules/dcr-cf52a36bb70546c69c09b3652b955588/streams/Microsoft-OTLP-Logs/otlp/v1/logs",
    "/v1/metrics": "https://managed-jinspark-insights-dce-4d93.eastus-1.metrics.ingest.monitor.azure.com/dataCollectionRules/dcr-cf52a36bb70546c69c09b3652b955588/streams/Microsoft-OtelMetrics/otlp/v1/metrics",
}
RESOURCE = "https://monitor.azure.com/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("otlp")

_token = {"value": "", "exp": 0}


def _token_request() -> urllib.request.Request:
    params = {"resource": RESOURCE}
    if os.environ.get("AZURE_CLIENT_ID"):
        params["client_id"] = os.environ["AZURE_CLIENT_ID"]
    identity_endpoint = os.environ.get("IDENTITY_ENDPOINT")
    if identity_endpoint:  # App Service managed identity
        params["api-version"] = "2019-08-01"
        return urllib.request.Request(
            f"{identity_endpoint}?{urllib.parse.urlencode(params)}",
            headers={"X-IDENTITY-HEADER": os.environ.get("IDENTITY_HEADER", "")},
        )
    params["api-version"] = "2018-02-01"
    return urllib.request.Request(
        "http://169.254.169.254/metadata/identity/oauth2/token?" + urllib.parse.urlencode(params),
        headers={"Metadata": "true"},
    )


def get_token() -> str:
    if time.time() > _token["exp"] - 300:
        with urllib.request.urlopen(_token_request(), timeout=5) as r:
            data = json.load(r)
        _token.update(value=data["access_token"], exp=int(data["expires_on"]))
    return _token["value"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.warning("HTTP %s: %s", self.client_address[0], fmt % args)

    def log_request(self, *args):
        pass

    def reply(self, status, payload=b"", ctype="application/x-protobuf"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        start = time.time()
        client = self.client_address[0]
        target = ENDPOINTS.get(self.path)
        if not target:
            log.warning("REJECT %s POST %s -> 404 unknown path", client, self.path)
            return self.reply(404)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        log.info("RECV   %s POST %s bytes=%d encoding=%s", client, self.path, len(body),
                 self.headers.get("Content-Encoding", "none"))
        try:
            headers = {"Authorization": f"Bearer {get_token()}",
                       "Content-Type": self.headers.get("Content-Type", "application/x-protobuf")}
            if self.headers.get("Content-Encoding"):
                headers["Content-Encoding"] = self.headers["Content-Encoding"]
            try:
                resp = urllib.request.urlopen(urllib.request.Request(target, body, headers), timeout=30)
            except urllib.error.HTTPError as e:
                resp = e
            payload, status = resp.read(), resp.code
        except Exception as e:
            log.error("FAIL   %s POST %s -> 502 %s: %s (%.0fms)", client, self.path,
                      type(e).__name__, e, (time.time() - start) * 1000)
            return self.reply(502, str(e).encode(), "text/plain")
        elapsed = (time.time() - start) * 1000
        if status < 400:
            log.info("FORWARD %s -> Azure %d (%.0fms)", self.path, status, elapsed)
        else:
            log.error("AZURE ERROR %s -> %d (%.0fms) body=%s", self.path, status, elapsed,
                      payload[:500].decode("utf-8", "replace"))
        self.reply(status, payload, resp.headers.get("Content-Type", "application/x-protobuf"))


def main() -> None:
    log.info("Listening on http://%s:%d", HOST, PORT)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.handle_error = lambda request, addr: log.warning(
        "CONNECTION ERROR %s: %s", addr[0], sys.exc_info()[1])
    httpd.serve_forever()


if __name__ == "__main__":
    main()
