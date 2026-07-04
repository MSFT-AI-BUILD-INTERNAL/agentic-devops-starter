"""Session isolation helpers shared across runtime and API layers."""

from __future__ import annotations

import hashlib
import os
import re

_SAFE_TOKEN_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")
_MAX_ISOLATION_ID_LENGTH = 64


def normalize_isolation_session_id(candidate: str | None, fallback: str) -> str:
    """Return a filesystem-safe session isolation token."""
    raw = (candidate or "").strip()
    base = raw if raw else fallback
    normalized = _SAFE_TOKEN_PATTERN.sub("-", base).strip("._-")
    if not normalized:
        normalized = "session"
    return normalized[:_MAX_ISOLATION_ID_LENGTH]


def build_pool_key(isolation_session_id: str, thread_id: str) -> str:
    """Build a key for in-memory session pool maps."""
    return f"{isolation_session_id}:{thread_id}"


def build_copilot_session_id(prefix: str, isolation_session_id: str, thread_id: str) -> str:
    """Build a deterministic Copilot session id isolated by session namespace."""
    seed = f"{prefix}:{isolation_session_id}:{thread_id}".encode()
    digest = hashlib.sha256(seed).hexdigest()[:20]
    return f"{prefix}-{isolation_session_id}-{digest}"


def build_config_dir(base_dir: str, isolation_session_id: str) -> str:
    """Build a per-session config directory path."""
    return os.path.join(base_dir, isolation_session_id)


def build_blob_prefix(isolation_session_id: str) -> str:
    """Return the blob prefix reserved for one isolation session."""
    return f"sessions/{isolation_session_id}/"


def build_namespaced_blob_name(isolation_session_id: str, leaf_blob_name: str) -> str:
    """Prefix a blob name with the isolation session namespace."""
    return f"{build_blob_prefix(isolation_session_id)}{leaf_blob_name}"


def is_blob_name_in_isolation(blob_name: str, isolation_session_id: str) -> bool:
    """Return whether a blob name belongs to the isolation session namespace."""
    return blob_name.startswith(build_blob_prefix(isolation_session_id))
