"""GitHub OAuth helpers for Copilot SDK user authentication."""

import base64
import secrets
import time
from dataclasses import dataclass
from functools import lru_cache

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import cmac, hashes
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException, Request, Response

from src.core.config import settings

SESSION_COOKIE = "github_oauth_session"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
_OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60
_FERNET_KEY_SALT = b"agentic-devops-starter/oauth-cookie-encryption/v1"
_OAUTH_CMAC_KEY_SALT = b"agentic-devops-starter/oauth-cmac-key/v1"
_oauth_states: dict[str, "OAuthStateEntry"] = {}


@dataclass(frozen=True)
class OAuthToken:
    """OAuth token returned by GitHub."""

    access_token: str


@dataclass(frozen=True)
class DeviceCodeResponse:
    """Device code data returned by GitHub's device authorization endpoint."""

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


@dataclass(frozen=True)
class DeviceTokenResult:
    """Result of a single device token poll."""

    session_token: str | None  # encrypted session token when status is "ok"
    status: str  # "ok" | "pending" | "slow_down" | "expired" | "denied"
    interval: int | None = None  # seconds to add to polling interval on slow_down


@dataclass(frozen=True)
class OAuthStateEntry:
    """Single-use OAuth state metadata."""

    expires_at: float
    context: str


def create_oauth_state(state_context: str) -> str:
    """Create and retain a single-use OAuth CSRF state token."""
    now = time.time()
    for expired_state, metadata in tuple(_oauth_states.items()):
        if metadata.expires_at < now:
            del _oauth_states[expired_state]
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = OAuthStateEntry(
        expires_at=now + _OAUTH_STATE_MAX_AGE_SECONDS,
        context=state_context,
    )
    return state


async def exchange_code(code: str) -> OAuthToken:
    """Exchange a GitHub authorization code for a user access token."""
    payload = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
    }
    if settings.github_oauth_redirect_uri:
        payload["redirect_uri"] = settings.github_oauth_redirect_uri

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json=payload,
        )
    response.raise_for_status()
    token_data = response.json()
    token = token_data.get("access_token")
    if not isinstance(token, str) or not token:
        raise HTTPException(status_code=401, detail="GitHub authorization failed")
    return OAuthToken(access_token=token)


async def request_device_code() -> DeviceCodeResponse:
    """Request a device code from GitHub to begin the Device Authorization Flow."""
    if not settings.github_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://github.com/login/device/code",
            headers={"Accept": "application/json"},
            json={"client_id": settings.github_client_id},
        )
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise HTTPException(status_code=503, detail=f"GitHub Device Flow error: {data['error']}")

    return DeviceCodeResponse(
        device_code=data["device_code"],
        user_code=data["user_code"],
        verification_uri=data["verification_uri"],
        expires_in=data["expires_in"],
        interval=data["interval"],
    )


async def poll_device_token(device_code: str) -> DeviceTokenResult:
    """Poll GitHub once for a Device Flow token. Returns the result immediately."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": settings.github_client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
    response.raise_for_status()
    data = response.json()

    error = data.get("error")
    if error == "authorization_pending":
        return DeviceTokenResult(session_token=None, status="pending")
    if error == "slow_down":
        # RFC 8628 §3.5: client must add 5 seconds to its polling interval
        return DeviceTokenResult(session_token=None, status="slow_down", interval=5)
    if error in ("expired_token", "device_flow_disabled"):
        return DeviceTokenResult(session_token=None, status="expired")
    if error == "access_denied":
        return DeviceTokenResult(session_token=None, status="denied")
    if error:
        raise HTTPException(status_code=502, detail=f"GitHub token exchange error: {error}")

    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=502, detail="GitHub returned an empty access token")

    session_token = store_token(OAuthToken(access_token=access_token))
    return DeviceTokenResult(session_token=session_token, status="ok")


def store_token(token: OAuthToken) -> str:
    """Encrypt a token for the opaque browser session cookie."""
    return _session_cipher(settings.github_client_secret).encrypt(token.access_token.encode()).decode()


def set_session_cookie(response: Response, session_id: str) -> None:
    """Attach the encrypted session cookie to *response* with canonical settings."""
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )


def verify_oauth_state(state: str, state_context: str) -> bool:
    """Consume and validate a single-use OAuth CSRF state token."""
    metadata = _oauth_states.pop(state, None)
    if not metadata or metadata.expires_at < time.time():
        return False
    return secrets.compare_digest(metadata.context, state_context)


def oauth_state_context(request: Request) -> str:
    """Return a browser-bound context value for OAuth state correlation."""
    client_host = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    return _oauth_cmac(f"{client_host}:{user_agent}".encode())


def get_user_token(request: Request) -> str:
    """Return the authenticated user's GitHub token or reject the request."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        session_token = auth_header[len("Bearer "):]
    elif auth_header:
        session_token = auth_header
    else:
        session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        raise HTTPException(status_code=401, detail="GitHub authentication required")
    try:
        return _session_cipher(settings.github_client_secret).decrypt(
            session_token.encode(), ttl=SESSION_MAX_AGE_SECONDS
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
