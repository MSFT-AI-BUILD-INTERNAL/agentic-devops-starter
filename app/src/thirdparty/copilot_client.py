"""Direct GitHub Copilot API client authenticated via a GitHub PAT.

This talks to GitHub Copilot's own HTTP API directly (as documented by the
reverse-engineered ``copilot-api`` project: https://github.com/ericc-ch/copilot-api)
instead of going through the Copilot SDK / CLI subprocess. A GitHub PAT is
exchanged for a short-lived Copilot token, which is then used to call the
OpenAI-compatible ``/chat/completions`` and ``/models`` endpoints on
``https://api.githubcopilot.com``.

There is no server-side session/conversation state: every request is
self-contained and forwards the caller's full message history, matching how
the real Anthropic and OpenAI APIs behave.
"""

import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import httpx

_COPILOT_VERSION = "0.26.7"
_EDITOR_VERSION = "vscode/1.96.0"
_EDITOR_PLUGIN_VERSION = f"copilot-chat/{_COPILOT_VERSION}"
_USER_AGENT = f"GitHubCopilotChat/{_COPILOT_VERSION}"
_API_VERSION = "2025-04-01"

_GITHUB_API_BASE_URL = "https://api.github.com"
_COPILOT_API_BASE_URL = "https://api.githubcopilot.com"

# Refresh the cached Copilot token a bit before its real expiry to avoid
# races with in-flight requests.
_REFRESH_SKEW_SECONDS = 60.0

_REQUEST_TIMEOUT_SECONDS = httpx.Timeout(120.0, connect=15.0)


class CopilotAPIError(RuntimeError):
    """Raised when the GitHub Copilot API rejects a token exchange or request."""


@dataclass
class _CachedCopilotToken:
    token: str
    expires_at: float  # epoch seconds


class CopilotClient:
    """Stateless-per-request GitHub Copilot API client for a single GitHub PAT.

    One instance should be reused across requests for the same PAT so the
    exchanged Copilot token is cached and only refreshed once it is close to
    expiry, rather than re-exchanged on every call.
    """

    def __init__(self, github_pat: str) -> None:
        self._github_pat = github_pat
        self._token: _CachedCopilotToken | None = None
        self._token_lock = asyncio.Lock()

    def _github_headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "accept": "application/json",
            "authorization": f"token {self._github_pat}",
            "editor-version": _EDITOR_VERSION,
            "editor-plugin-version": _EDITOR_PLUGIN_VERSION,
            "user-agent": _USER_AGENT,
            "x-github-api-version": _API_VERSION,
        }

    async def _get_copilot_token(self) -> str:
        """Return a cached Copilot token, exchanging/refreshing it as needed."""
        async with self._token_lock:
            now = time.time()
            cached = self._token
            if cached is not None and cached.expires_at - _REFRESH_SKEW_SECONDS > now:
                return cached.token

            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{_GITHUB_API_BASE_URL}/copilot_internal/v2/token",
                    headers=self._github_headers(),
                )
            if response.status_code != 200:
                raise CopilotAPIError(
                    f"Failed to exchange GitHub PAT for a Copilot token "
                    f"(HTTP {response.status_code}): {response.text}"
                )
            data = response.json()
            token = data.get("token")
            expires_at = data.get("expires_at")
            if not isinstance(token, str) or not token or not expires_at:
                raise CopilotAPIError(
                    "Copilot token response is missing 'token'/'expires_at'."
                )
            self._token = _CachedCopilotToken(token=token, expires_at=float(expires_at))
            return self._token.token

    async def _copilot_headers(self) -> dict[str, str]:
        token = await self._get_copilot_token()
        return {
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "copilot-integration-id": "vscode-chat",
            "editor-version": _EDITOR_VERSION,
            "editor-plugin-version": _EDITOR_PLUGIN_VERSION,
            "user-agent": _USER_AGENT,
            "openai-intent": "conversation-panel",
            "x-github-api-version": _API_VERSION,
            "x-request-id": str(uuid.uuid4()),
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """Return the raw model list from the Copilot ``/models`` endpoint."""
        headers = await self._copilot_headers()
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{_COPILOT_API_BASE_URL}/models", headers=headers)
        if response.status_code != 200:
            raise CopilotAPIError(
                f"Failed to list Copilot models (HTTP {response.status_code}): {response.text}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise CopilotAPIError("Unexpected response shape from Copilot /models endpoint.")
        models = data.get("data", [])
        if not isinstance(models, list) or not all(isinstance(model, dict) for model in models):
            raise CopilotAPIError("Unexpected response shape from Copilot /models endpoint.")
        return models

    async def create_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform a non-streaming chat completion call and return the parsed JSON body."""
        headers = await self._copilot_headers()
        headers["x-initiator"] = _initiator_for(payload)
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{_COPILOT_API_BASE_URL}/chat/completions", headers=headers, json=payload
            )
        if response.status_code != 200:
            raise CopilotAPIError(
                f"Copilot chat completion request failed "
                f"(HTTP {response.status_code}): {response.text}"
            )
        return response.json()

    async def stream_chat_completion(
        self, payload: dict[str, Any]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Perform a streaming chat completion call, yielding each parsed SSE chunk."""
        headers = await self._copilot_headers()
        headers["x-initiator"] = _initiator_for(payload)
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                f"{_COPILOT_API_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise CopilotAPIError(
                        f"Copilot chat completion request failed "
                        f"(HTTP {response.status_code}): {body.decode(errors='replace')}"
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data or data == "[DONE]":
                        continue
                    yield json.loads(data)


def _initiator_for(payload: dict[str, Any]) -> str:
    """Return the ``X-Initiator`` header value: "agent" if any message is
    from an assistant/tool, otherwise "user" (mirrors copilot-api)."""
    for message in payload.get("messages", []):
        if message.get("role") in ("assistant", "tool"):
            return "agent"
    return "user"


# One client per configured GitHub PAT, so the exchanged Copilot token is
# cached/reused across requests instead of re-exchanged every call.
_clients: dict[str, CopilotClient] = {}


def get_copilot_client(github_pat: str) -> CopilotClient:
    """Return the shared :class:`CopilotClient` for *github_pat*, creating it if needed."""
    client = _clients.get(github_pat)
    if client is None:
        client = CopilotClient(github_pat)
        _clients[github_pat] = client
    return client
