"""GitHub OAuth helpers for Copilot SDK user authentication."""

import base64
from functools import lru_cache
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException, Request

from src.core.config import settings

_SESSION_COOKIE = "github_oauth_session"
_OAUTH_NONCE_COOKIE = "github_oauth_nonce"
_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
_OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60
_FERNET_KEY_SALT = b"agentic-devops-starter/oauth-cookie-encryption/v1"


@dataclass(frozen=True)
class OAuthToken:
    """OAuth token returned by GitHub."""

    access_token: str


def create_oauth_nonce() -> str:
    """Create an opaque nonce for the HttpOnly OAuth correlation cookie."""
    return secrets.token_urlsafe(32)


def create_oauth_state(nonce: str) -> str:
    """Create an expiry-bound OAuth CSRF state token for a browser nonce."""
    expires_at = int(time.time()) + _OAUTH_STATE_MAX_AGE_SECONDS
    payload = f"{nonce}.{expires_at}".encode()
    signature = _oauth_hmac(payload)
    return f"{expires_at}.{signature}"


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
    return _session_cipher(settings.github_client_secret).encrypt(token.access_token.encode()).decode()


def verify_oauth_state(nonce: str, state: str) -> bool:
    """Return whether a callback state token is valid for the browser nonce."""
    try:
        expires_at_text, _ = state.split(".", maxsplit=1)
        expires_at = int(expires_at_text)
    except (ValueError, AttributeError):
        return False
    if not nonce or expires_at < time.time():
        return False
    expected_state = f"{expires_at}.{_oauth_hmac(f'{nonce}.{expires_at}'.encode())}"
    return hmac.compare_digest(expected_state, state)


def get_user_token(request: Request) -> str:
    """Return the authenticated user's GitHub token or reject the request."""
    session_id = request.cookies.get(_SESSION_COOKIE)
    if not session_id:
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    try:
        return _session_cipher(settings.github_client_secret).decrypt(
            session_id.encode(), ttl=_SESSION_MAX_AGE_SECONDS
        ).decode()
    except (InvalidToken, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="GitHub authentication required") from None


def get_user_session_id(request: Request) -> str:
    """Return a stable, non-secret namespace for the authenticated user token."""
    return _oauth_hmac(get_user_token(request).encode())


@lru_cache
def _session_cipher(client_secret: str) -> Fernet:
    """Build a cookie cipher from the GitHub App client secret."""
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_FERNET_KEY_SALT,
        iterations=600_000,
    ).derive(client_secret.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def initialize_session_cipher() -> None:
    """Warm the OAuth cookie cipher cache when OAuth is configured."""
    if settings.github_client_secret:
        _session_cipher(settings.github_client_secret)


def _oauth_hmac(payload: bytes) -> str:
    """Return a URL-safe HMAC for an OAuth value without exposing the key."""
    digest = hmac.new(settings.github_client_secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
