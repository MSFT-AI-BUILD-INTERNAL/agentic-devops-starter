"""GitHub OAuth helpers for Copilot SDK user authentication."""

import base64
from functools import lru_cache
import secrets
import time
from dataclasses import dataclass

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import cmac, hashes
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException, Request

from src.core.config import settings

_SESSION_COOKIE = "github_oauth_session"
_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
_OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60
_FERNET_KEY_SALT = b"agentic-devops-starter/oauth-cookie-encryption/v1"
_OAUTH_CMAC_KEY_SALT = b"agentic-devops-starter/oauth-cmac-key/v1"
_oauth_states: dict[str, float] = {}


@dataclass(frozen=True)
class OAuthToken:
    """OAuth token returned by GitHub."""

    access_token: str


def create_oauth_state() -> str:
    """Create and retain a single-use OAuth CSRF state token."""
    now = time.time()
    for expired_state, expires_at in tuple(_oauth_states.items()):
        if expires_at < now:
            del _oauth_states[expired_state]
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = now + _OAUTH_STATE_MAX_AGE_SECONDS
    return state


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


def verify_oauth_state(state: str) -> bool:
    """Consume and validate a single-use OAuth CSRF state token."""
    return _oauth_states.pop(state, 0) >= time.time()


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
    return _oauth_cmac(get_user_token(request).encode())


def get_user_isolation_namespace(session_id: str, client_isolation_id: str) -> str:
    """Return an authenticated namespace for a client-selected isolation ID."""
    return _oauth_cmac(f"{session_id}:{client_isolation_id}".encode())


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
    """Warm OAuth cryptographic key caches when OAuth is configured."""
    if settings.github_client_secret:
        _session_cipher(settings.github_client_secret)
        _oauth_cmac_key(settings.github_client_secret)


def _oauth_cmac(payload: bytes) -> str:
    """Return a URL-safe CMAC for an OAuth value without exposing the key."""
    signer = cmac.CMAC(algorithms.AES(_oauth_cmac_key(settings.github_client_secret)))
    signer.update(payload)
    digest = signer.finalize()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@lru_cache
def _oauth_cmac_key(client_secret: str) -> bytes:
    """Derive a separate key for OAuth CMAC operations."""
    return PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_OAUTH_CMAC_KEY_SALT,
        iterations=600_000,
    ).derive(client_secret.encode())
