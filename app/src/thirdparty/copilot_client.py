"""Direct GitHub Copilot API client authenticated with a fine-grained PAT.

Fine-grained PATs with the ``Copilot Requests`` account permission are sent
directly to GitHub Copilot's OpenAI-compatible API. No Copilot SDK, CLI
subprocess, device flow, or intermediate token exchange is involved.

There is no server-side session/conversation state: every request is
self-contained and forwards the caller's full message history, matching how
the real Anthropic and OpenAI APIs behave.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx

_COPILOT_API_BASE_URL = "https://api.githubcopilot.com"
_REQUEST_TIMEOUT_SECONDS = httpx.Timeout(120.0, connect=15.0)


class CopilotAPIError(RuntimeError):
    """Raised when the GitHub Copilot API rejects a request."""


class CopilotClient:
    """Stateless GitHub Copilot API client for one fine-grained PAT."""

    def __init__(self, github_pat: str) -> None:
        self._github_pat = github_pat

    def _copilot_headers(self) -> dict[str, str]:
        if not self._github_pat.startswith("github_pat_"):
            raise CopilotAPIError(_credential_error_hint(self._github_pat))

        return {
            "authorization": self._github_pat,
            "content-type": "application/json",
            "copilot-integration-id": "copilot-developer-cli",
            "x-request-id": str(uuid.uuid4()),
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """Return the raw model list from the Copilot ``/models`` endpoint."""
        headers = self._copilot_headers()
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
        headers = self._copilot_headers()
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
        headers = self._copilot_headers()
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


def _credential_error_hint(token: str) -> str:
    """Return safe troubleshooting guidance without exposing the credential."""
    if token.startswith("ghp_"):
        return (
            "Classic GitHub PATs are not supported. Use a personal-account-owned "
            "fine-grained PAT with the 'Copilot Requests' account permission."
        )
    return (
        "THIRDPARTY_GITHUB_PAT must be a personal-account-owned fine-grained PAT "
        "with the 'Copilot Requests' account permission."
    )


def get_copilot_client(github_pat: str) -> CopilotClient:
    """Return a direct Copilot API client for *github_pat*."""
    return CopilotClient(github_pat)
