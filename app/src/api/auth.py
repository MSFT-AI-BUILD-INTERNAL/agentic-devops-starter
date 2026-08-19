"""GitHub OAuth helpers for Copilot SDK user authentication."""

import base64
import hashlib
import secrets
from dataclasses import dataclass

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request

from src.core.config import settings

_SESSION_COOKIE = "github_oauth_session"
_STATE_COOKIE = "github_oauth_state"
_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60


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
    """Encrypt a token for the opaque browser session cookie."""
    return _session_cipher().encrypt(token.access_token.encode()).decode()


def get_user_token(request: Request) -> str:
    """Return the authenticated user's GitHub token or reject the request."""
    session_id = request.cookies.get(_SESSION_COOKIE)
    if not session_id:
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    try:
        return _session_cipher().decrypt(
            session_id.encode(), ttl=_SESSION_MAX_AGE_SECONDS
        ).decode()
    except (InvalidToken, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="GitHub authentication required") from None


def get_user_session_id(request: Request) -> str:
    """Return a stable, non-secret namespace for the authenticated user token."""
    return hashlib.sha256(get_user_token(request).encode()).hexdigest()


def _session_cipher() -> Fernet:
    """Build a cookie cipher from the GitHub App client secret."""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.github_client_secret.encode()).digest())
    return Fernet(key)
