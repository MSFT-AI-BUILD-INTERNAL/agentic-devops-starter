"""Azure Blob Storage helper for the file upload feature.

The backend uploads user files to the configured Blob container using the
App Service managed identity (in production) or developer credentials
(locally), then downloads the blob to feed its contents into the Copilot SDK
session for processing.

The Azure SDK's ``upload_blob`` uses multi-part (block) uploads under the
hood when the data exceeds a single block size, satisfying the issue's
"multi-part upload via web app" requirement without any custom chunking.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import IO, BinaryIO

from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient

# Block size for multi-part uploads. The Azure SDK auto-chunks data larger
# than this into separate block uploads that are committed atomically.
_BLOCK_SIZE_BYTES = 4 * 1024 * 1024  # 4 MiB
# Maximum number of bytes downloaded from blob and forwarded to Copilot.
# Prevents oversized files from blowing up the model context window.
_MAX_PROCESS_BYTES = 1 * 1024 * 1024  # 1 MiB


@dataclass(frozen=True)
class UploadedBlob:
    """Metadata returned after a successful upload."""

    name: str
    container: str
    size: int
    content_type: str | None


class BlobStorageClient:
    """Thin async wrapper around :class:`BlobServiceClient`.

    Initialised once at application startup and torn down at shutdown.
    """

    def __init__(
        self,
        account_url: str,
        container_name: str,
        credential: AsyncTokenCredential | None = None,
    ) -> None:
        self._account_url = account_url
        self._container_name = container_name
        # Caller may pass a credential (e.g. for tests); otherwise use the
        # default Entra ID credential chain (managed identity in App Service,
        # developer credentials locally).
        self._credential: AsyncTokenCredential = credential or DefaultAzureCredential()
        self._service_client = BlobServiceClient(
            account_url=account_url, credential=self._credential
        )

    @property
    def container_name(self) -> str:
        return self._container_name

    async def close(self) -> None:
        """Release the underlying SDK and credential clients."""
        await self._service_client.close()
        close = getattr(self._credential, "close", None)
        if callable(close):
            await close()

    async def upload(
        self,
        stream: IO[bytes] | BinaryIO,
        original_filename: str,
        content_type: str | None,
    ) -> UploadedBlob:
        """Upload *stream* to the configured container using multi-part uploads.

        A random prefix is added to avoid collisions and to keep the original
        filename for the user's reference.
        """
        safe_name = os.path.basename(original_filename or "upload.bin")
        blob_name = f"{uuid.uuid4().hex}-{safe_name}"

        blob_client = self._service_client.get_blob_client(
            container=self._container_name, blob=blob_name
        )
        # ``upload_blob`` performs a multi-part (block) upload automatically
        # for inputs larger than the block size.
        await blob_client.upload_blob(
            stream,
            overwrite=False,
            max_concurrency=4,
            length=None,
            content_settings=_content_settings(content_type),
        )

        properties = await blob_client.get_blob_properties()
        return UploadedBlob(
            name=blob_name,
            container=self._container_name,
            size=int(properties.size or 0),
            content_type=content_type,
        )

    async def download_text(self, blob_name: str) -> str:
        """Download a blob and return its contents decoded as UTF-8 text.

        Truncates to ``_MAX_PROCESS_BYTES`` to keep prompts bounded. Bytes
        that cannot be decoded as UTF-8 are replaced rather than raising,
        because the downstream consumer is an LLM and any best-effort text
        view is acceptable for processing.
        """
        blob_client = self._service_client.get_blob_client(
            container=self._container_name, blob=blob_name
        )
        downloader = await blob_client.download_blob(offset=0, length=_MAX_PROCESS_BYTES)
        data: bytes = await downloader.readall()
        return data.decode("utf-8", errors="replace")


def _content_settings(content_type: str | None) -> ContentSettings | None:
    """Build ContentSettings only when a content_type is provided."""
    if not content_type:
        return None
    return ContentSettings(content_type=content_type)


__all__ = [
    "BlobStorageClient",
    "UploadedBlob",
    "_BLOCK_SIZE_BYTES",
    "_MAX_PROCESS_BYTES",
]
