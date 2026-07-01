"""Use cases for file uploads."""

from fastapi import UploadFile
from fastapi.responses import JSONResponse

from src.blob_storage import BlobStorageConfigurationError, get_blob_service
from src.config import settings
from src.error_handler import log_and_respond
from src.file_validation import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
    generate_blob_name,
    resolve_content_type,
    validate_file_size,
    validate_file_type,
)
from src.logging_utils import setup_logging
from src.models import UploadResult

logger = setup_logging(settings.log_level)


async def upload_file_to_blob(file: UploadFile) -> JSONResponse:
    """Upload a file to Azure Blob Storage."""
    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_file_type(content_type, filename)
    except ValueError:
        return log_and_respond(
            logger,
            415,
            "INVALID_TYPE",
            "File type is not allowed.",
            "Rejected file upload due to invalid content type",
            extra={"upload_filename": filename, "content_type": content_type},
            extra_fields={"allowed_types": sorted(ALLOWED_CONTENT_TYPES)},
        )

    content_type = resolve_content_type(content_type, filename)
    content = await file.read()
    size_bytes = len(content)

    try:
        validate_file_size(size_bytes)
    except ValueError:
        is_empty = size_bytes == 0
        status = 422 if is_empty else 413
        error_code = "EMPTY_FILE" if is_empty else "FILE_TOO_LARGE"
        detail = "File is empty." if is_empty else "File exceeds the maximum allowed size."
        return log_and_respond(
            logger,
            status,
            error_code,
            detail,
            "Rejected file upload due to invalid file size",
            extra={"upload_filename": filename, "size_bytes": size_bytes},
            extra_fields={"max_size_bytes": MAX_FILE_SIZE_BYTES},
        )

    blob_name = generate_blob_name(filename)
    try:
        blob_service = get_blob_service()
        blob_service.upload(content, blob_name, content_type)
    except BlobStorageConfigurationError as exc:
        return log_and_respond(
            logger,
            503,
            "STORAGE_NOT_CONFIGURED",
            "Blob storage is not configured on this server. "
            "Set COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT to a valid "
            "https://<account>.blob.core.windows.net URL.",
            "Blob upload failed: storage is not configured",
            extra={"upload_filename": filename},
            exception=exc,
        )
    except Exception as exc:
        return log_and_respond(
            logger,
            502,
            "UPLOAD_FAILED",
            "Failed to upload file to storage",
            "Blob upload failed",
            extra={"upload_filename": filename},
            exception=exc,
        )

    result = UploadResult(
        blob_name=blob_name,
        original_filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )
    return JSONResponse(status_code=200, content=result.model_dump())
