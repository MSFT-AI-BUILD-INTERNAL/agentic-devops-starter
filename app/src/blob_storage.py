"""Azure Blob Storage service for file upload/download."""

import logging
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from src.config import settings
from src.logging_utils import setup_logging

logger: logging.Logger = setup_logging(settings.log_level)


class BlobStorageConfigurationError(RuntimeError):
    """Raised when blob storage settings are missing or invalid.

    Distinct from runtime upload/download failures so callers can return a
    503 (Service Unavailable) with an actionable message instead of masking
    a misconfiguration as a generic upstream failure.
    """


class BlobStorageService:
    """Handles upload and download operations to Azure Blob Storage."""

    def __init__(self, endpoint: str, container_name: str) -> None:
        self._container_name = container_name
        credential = DefaultAzureCredential()
        self._client = BlobServiceClient(account_url=endpoint, credential=credential)

    async def upload(self, file_content: bytes, blob_name: str, content_type: str) -> str:
        """Upload file content to blob storage.

        Returns the blob name on success.
        """
        container_client = self._client.get_container_client(self._container_name)
        blob_client = container_client.get_blob_client(blob_name)

        content_settings = ContentSettings(content_type=content_type)
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=content_settings,
        )

        logger.info("Blob uploaded", extra={"blob_name": blob_name, "size": len(file_content)})
        return blob_name

    async def download(self, blob_name: str) -> bytes:
        """Download blob content by name."""
        container_client = self._client.get_container_client(self._container_name)
        blob_client = container_client.get_blob_client(blob_name)

        downloader = blob_client.download_blob()
        content: bytes = downloader.readall()

        logger.info("Blob downloaded", extra={"blob_name": blob_name, "size": len(content)})
        return content


def get_blob_service() -> BlobStorageService:
    """Get the singleton BlobStorageService instance.

    Raises:
        BlobStorageConfigurationError: if the configured endpoint is missing
            or not a valid ``http(s)://host`` URL. This typically means the
            ``COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT`` env var was not set
            on the host (e.g. App Service app settings were not applied).
    """
    endpoint = settings.azure_storage_blob_endpoint
    if not endpoint or not endpoint.strip():
        raise BlobStorageConfigurationError(
            "Azure Blob Storage endpoint is not configured "
            "(set COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT)."
        )
    parsed = urlparse(endpoint.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise BlobStorageConfigurationError(
            "Azure Blob Storage endpoint is not a valid http(s) URL "
            "(check COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT)."
        )
    return BlobStorageService(
        endpoint=endpoint,
        container_name=settings.azure_storage_container_name,
    )
