"""File validation utilities for upload processing."""

import re
import uuid

MAX_FILE_SIZE_BYTES: int = 10_485_760  # 10 MB
MAX_FILES_PER_MESSAGE: int = 3
ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "text/plain",
    "text/csv",
    "application/json",
    "text/markdown",
}
ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".txt", ".csv", ".json", ".md",
}
EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".md": "text/markdown",
}
# Generic content types browsers/OS send when they cannot detect a specific MIME type.
GENERIC_CONTENT_TYPES: set[str] = {"application/octet-stream", ""}
MAX_FILENAME_LENGTH: int = 200


def validate_file_type(content_type: str, filename: str) -> None:
    """Validate that the file type is allowed.

    The file extension is the source of truth: browsers and operating systems
    are inconsistent about the ``Content-Type`` they attach to common file
    types (for example ``.md`` is often sent as ``application/octet-stream``).
    A specific content type, when provided, must still match the allow list.

    Raises ValueError if the extension is not supported, or if a specific
    (non-generic) content type is provided but not in the allowed set.
    """
    allowed_exts = ", ".join(sorted(ALLOWED_EXTENSIONS))
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. Supported extensions: {allowed_exts}"
        )

    if content_type in GENERIC_CONTENT_TYPES:
        return

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Unsupported file type '{content_type}'. Supported extensions: {allowed_exts}"
        )


def resolve_content_type(content_type: str, filename: str) -> str:
    """Return a specific content type, inferring from the extension when generic."""
    if content_type and content_type not in GENERIC_CONTENT_TYPES:
        return content_type
    ext = _get_extension(filename)
    return EXTENSION_CONTENT_TYPES.get(ext, content_type or "application/octet-stream")


def validate_file_size(size: int) -> None:
    """Validate that the file size is within limits.

    Raises ValueError if the file is empty or exceeds the maximum size.
    """
    if size <= 0:
        raise ValueError("File is empty")
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
        )


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe blob storage.

    Strips directory components, removes unsafe characters, truncates to
    MAX_FILENAME_LENGTH, and preserves the file extension.
    """
    # Strip directory components (path traversal prevention)
    filename = filename.replace("\\", "/").split("/")[-1]

    # Strip leading dots (hidden files)
    filename = filename.lstrip(".")

    if not filename:
        filename = "unnamed"

    # Separate name and extension
    ext = _get_extension(filename)
    name = filename[: -len(ext)] if ext else filename

    # Remove non-ASCII and unsafe characters, keep alphanumeric, hyphens, underscores, dots
    name = re.sub(r"[^\w\-.]", "_", name)
    # Collapse multiple underscores/dots
    name = re.sub(r"[_.]{2,}", "_", name)
    # Strip leading/trailing underscores
    name = name.strip("_")

    if not name:
        name = "file"

    # Truncate name to fit within MAX_FILENAME_LENGTH (including extension)
    max_name_len = MAX_FILENAME_LENGTH - len(ext)
    name = name[:max_name_len]

    return name + ext


def generate_blob_name(filename: str) -> str:
    """Generate a unique blob name from a sanitized filename."""
    sanitized = sanitize_filename(filename)
    return f"{uuid.uuid4().hex}_{sanitized}"


def _get_extension(filename: str) -> str:
    """Extract lowercase file extension including the dot."""
    dot_idx = filename.rfind(".")
    if dot_idx > 0:
        return filename[dot_idx:].lower()
    return ""
