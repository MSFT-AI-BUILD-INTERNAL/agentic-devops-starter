"""Tests for the Azure App Configuration feature-flag helper."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError


@pytest.mark.asyncio
async def test_is_feature_enabled_returns_default_when_endpoint_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When AZURE_APPCONFIG_ENDPOINT is unset we return the caller default."""
    monkeypatch.delenv("AZURE_APPCONFIG_ENDPOINT", raising=False)
    from feature_flags import is_feature_enabled

    assert await is_feature_enabled("Beta", default=False) is False
    assert await is_feature_enabled("Beta", default=True) is True


@pytest.mark.asyncio
async def test_is_feature_enabled_returns_true_for_enabled_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A flag whose JSON payload has ``enabled: true`` returns True."""
    monkeypatch.setenv("AZURE_APPCONFIG_ENDPOINT", "https://example.azconfig.io")
    from feature_flags import is_feature_enabled

    setting = MagicMock()
    setting.value = json.dumps({"id": "Beta", "enabled": True, "conditions": {}})

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get_configuration_setting = AsyncMock(return_value=setting)

    fake_credential = MagicMock()
    fake_credential.close = AsyncMock(return_value=None)

    with (
        patch("feature_flags.AzureAppConfigurationClient", return_value=fake_client) as mk_client,
        patch("feature_flags.DefaultAzureCredential", return_value=fake_credential),
    ):
        assert await is_feature_enabled("Beta") is True

    mk_client.assert_called_once()
    fake_client.get_configuration_setting.assert_awaited_once()
    args, kwargs = fake_client.get_configuration_setting.call_args
    assert kwargs["key"] == ".appconfig.featureflag/Beta"


@pytest.mark.asyncio
async def test_is_feature_enabled_returns_false_for_disabled_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A flag whose JSON payload has ``enabled: false`` returns False."""
    monkeypatch.setenv("AZURE_APPCONFIG_ENDPOINT", "https://example.azconfig.io")
    from feature_flags import is_feature_enabled

    setting = MagicMock()
    setting.value = json.dumps({"id": "Beta", "enabled": False, "conditions": {}})

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get_configuration_setting = AsyncMock(return_value=setting)

    fake_credential = MagicMock()
    fake_credential.close = AsyncMock(return_value=None)

    with (
        patch("feature_flags.AzureAppConfigurationClient", return_value=fake_client),
        patch("feature_flags.DefaultAzureCredential", return_value=fake_credential),
    ):
        assert await is_feature_enabled("Beta", default=True) is False


@pytest.mark.asyncio
async def test_is_feature_enabled_returns_default_when_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing flag returns the caller default (does not raise)."""
    monkeypatch.setenv("AZURE_APPCONFIG_ENDPOINT", "https://example.azconfig.io")
    from feature_flags import is_feature_enabled

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get_configuration_setting = AsyncMock(
        side_effect=ResourceNotFoundError("flag missing")
    )

    fake_credential = MagicMock()
    fake_credential.close = AsyncMock(return_value=None)

    with (
        patch("feature_flags.AzureAppConfigurationClient", return_value=fake_client),
        patch("feature_flags.DefaultAzureCredential", return_value=fake_credential),
    ):
        assert await is_feature_enabled("Missing", default=False) is False
        assert await is_feature_enabled("Missing", default=True) is True


def test_parse_feature_flag_enabled_handles_invalid_json() -> None:
    """Malformed payloads return the caller default rather than raising."""
    from feature_flags import _parse_feature_flag_enabled

    assert _parse_feature_flag_enabled("not-json", default=False) is False
    assert _parse_feature_flag_enabled("not-json", default=True) is True
    assert _parse_feature_flag_enabled(None, default=True) is True
    assert _parse_feature_flag_enabled("", default=True) is True


def test_parse_feature_flag_enabled_unexpected_shape() -> None:
    """A non-dict JSON payload returns the caller default."""
    from feature_flags import _parse_feature_flag_enabled

    payload: Any = json.dumps([1, 2, 3])
    assert _parse_feature_flag_enabled(payload, default=False) is False
