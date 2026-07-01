"""Tests for the blob storage service configuration handling."""

import pytest

from src.storage import blob_storage
from src.storage.blob_storage import BlobStorageConfigurationError, get_blob_service


@pytest.mark.parametrize("bad_endpoint", ["", "   ", "not-a-url", "ftp://example.com"])
def test_get_blob_service_raises_on_invalid_endpoint(
    monkeypatch: pytest.MonkeyPatch, bad_endpoint: str
) -> None:
    """An empty or non-http(s) endpoint must raise a typed configuration error.

    Regression test: previously an empty endpoint reached the Azure SDK which
    prepended ``https://`` and failed with the opaque ``Invalid URL: https://``.
    """
    monkeypatch.setattr(blob_storage.settings, "azure_storage_blob_endpoint", bad_endpoint)
    with pytest.raises(BlobStorageConfigurationError):
        get_blob_service()


def test_get_blob_service_accepts_valid_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """A well-formed https endpoint must construct a service without error."""
    monkeypatch.setattr(
        blob_storage.settings,
        "azure_storage_blob_endpoint",
        "https://example.blob.core.windows.net",
    )
    monkeypatch.setattr(blob_storage.settings, "azure_storage_container_name", "uploads")
    service = get_blob_service()
    assert service is not None
