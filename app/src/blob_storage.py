"""Azure Blob Storage service for file upload/download."""

import logging
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from src.config import settings
from src.logging_utils import setup_logging

logger: logging.Logger = setup_logging(settings.log_level)


class BlobStorageConfigurationError(RuntimeError):
    """Raised when blob storage settings are missing or invalid."""


class BlobStorageService:
    """Handles upload and download operations to Azure Blob Storage."""

    def __init__(self, endpoint: str, container_name: str) -> None:
        credential = DefaultAzureCredential()
        self._client = BlobServiceClient(account_url=endpoint, credential=credential)
        self._container_client = self._client.get_container_client(container_name)

    def upload(self, file_content: bytes, blob_name: str, content_type: str) -> str:
        """Upload file content to blob storage. Returns the blob name."""
        blob_client = self._container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type=content_type)
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=content_settings,
        )

        logger.info("Blob uploaded", extra={"blob_name": blob_name, "size": len(file_content)})
        return blob_name

    def download(self, blob_name: str) -> bytes:
        """Download blob content by name."""
        blob_client = self._container_client.get_blob_client(blob_name)
        downloader = blob_client.download_blob()
        content: bytes = downloader.readall()

        logger.info("Blob downloaded", extra={"blob_name": blob_name, "size": len(content)})
        return content


def get_blob_service() -> BlobStorageService:
    """Create a BlobStorageService from application settings.

    Raises BlobStorageConfigurationError if the endpoint is missing or invalid.
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
