"""GitHub OAuth helpers for Copilot SDK user authentication."""

import secrets
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request

from src.core.config import settings

_SESSION_COOKIE = "github_oauth_session"
_STATE_COOKIE = "github_oauth_state"
_tokens: dict[str, str] = {}


@dataclass(frozen=True)
class OAuthToken:
    """OAuth token returned by GitHub."""

    access_token: str


def create_oauth_state() -> str:
    """Create an OAuth CSRF state value bound to an HttpOnly browser cookie."""
    return secrets.token_urlsafe(32)


async def exchange_code(code: str) -> OAuthToken:
    """Exchange a GitHub authorization code for a user access token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
        )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise HTTPException(status_code=401, detail="GitHub authorization failed")
    return OAuthToken(access_token=token)


def store_token(token: OAuthToken) -> str:
    """Store a token server-side and return its opaque browser session ID."""
    session_id = secrets.token_urlsafe(32)
    _tokens[session_id] = token.access_token
    return session_id


def get_user_token(request: Request) -> str:
    """Return the authenticated user's GitHub token or reject the request."""
    session_id = request.cookies.get(_SESSION_COOKIE)
    token = _tokens.get(session_id or "")
    if token is None:
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    return token


def get_user_session_id(request: Request) -> str:
    """Return the opaque ID for the authenticated browser session."""
    session_id = request.cookies.get(_SESSION_COOKIE)
    if session_id not in _tokens:
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    return session_id


def clear_token(request: Request) -> None:
    """Remove the authenticated user's server-side token."""
    session_id = request.cookies.get(_SESSION_COOKIE)
    if session_id:
        _tokens.pop(session_id, None)
