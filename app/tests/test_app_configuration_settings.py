"""Tests for Azure App Configuration integration in config loading."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import Settings, apply_app_configuration


def _make_item(key: str, value: str) -> MagicMock:
    """Create a mock AzureAppConfigurationClient setting item."""
    item = MagicMock()
    item.key = key
    item.value = value
    return item


class TestApplyAppConfigurationNoop:
    """apply_app_configuration must be a no-op when no endpoint is configured."""

    def test_noop_when_endpoint_empty(self) -> None:
        """No Azure SDK calls when endpoint is empty."""
        s = Settings(app_config_endpoint="")
        with patch("azure.appconfiguration.AzureAppConfigurationClient") as mock_cls:
            apply_app_configuration(s)
        mock_cls.assert_not_called()

    def test_noop_does_not_change_defaults(self) -> None:
        """Settings remain at their defaults when endpoint is not set."""
        s = Settings(app_config_endpoint="")
        original_auth_mode = s.foundry_auth_mode
        apply_app_configuration(s)
        assert s.foundry_auth_mode == original_auth_mode


class TestApplyAppConfigurationAppliesValues:
    """App Configuration values are applied to the Settings object."""

    def test_applies_value_using_full_key(self) -> None:
        """An App Config key with full COPILOT_API_ prefix is applied correctly."""
        s = Settings(app_config_endpoint="https://example.azconfig.io")
        item = _make_item("COPILOT_API_FOUNDRY_AUTH_MODE", "azure_identity")

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.return_value = [item]
            apply_app_configuration(s)

        assert s.foundry_auth_mode == "azure_identity"

    def test_applies_value_using_bare_key(self) -> None:
        """An App Config key without the COPILOT_API_ prefix is also applied."""
        s = Settings(app_config_endpoint="https://example.azconfig.io")
        item = _make_item("foundry_wire_api", "completions")

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.return_value = [item]
            apply_app_configuration(s)

        assert s.foundry_wire_api == "completions"

    def test_unknown_key_is_silently_skipped(self) -> None:
        """Unknown App Config keys do not raise errors."""
        s = Settings(app_config_endpoint="https://example.azconfig.io")
        item = _make_item("SOME_UNKNOWN_FEATURE_FLAG", "true")

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.return_value = [item]
            apply_app_configuration(s)  # must not raise

    def test_label_filter_is_passed_to_client(self) -> None:
        """The app_config_label setting is forwarded as label_filter."""
        s = Settings(
            app_config_endpoint="https://example.azconfig.io",
            app_config_label="production",
        )

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.return_value = []
            apply_app_configuration(s)
            MockClient.return_value.list_configuration_settings.assert_called_once_with(
                label_filter="production"
            )

    def test_empty_label_passes_none_filter(self) -> None:
        """An empty app_config_label results in label_filter=None (no filter)."""
        s = Settings(
            app_config_endpoint="https://example.azconfig.io",
            app_config_label="",
        )

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.return_value = []
            apply_app_configuration(s)
            MockClient.return_value.list_configuration_settings.assert_called_once_with(
                label_filter=None
            )


class TestApplyAppConfigurationEnvVarPrecedence:
    """Environment variables must override App Configuration values."""

    def test_env_var_overrides_app_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A key already present in os.environ is never overwritten by App Config."""
        monkeypatch.setenv("COPILOT_API_FOUNDRY_AUTH_MODE", "api_key")
        s = Settings(app_config_endpoint="https://example.azconfig.io")
        # Settings picks up COPILOT_API_FOUNDRY_AUTH_MODE from env
        assert s.foundry_auth_mode == "api_key"

        item = _make_item("COPILOT_API_FOUNDRY_AUTH_MODE", "azure_identity")

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.return_value = [item]
            apply_app_configuration(s)

        # env var wins; App Config value must not take effect
        assert s.foundry_auth_mode == "api_key"


class TestApplyAppConfigurationErrorHandling:
    """App Configuration failures must be non-fatal."""

    def test_sdk_exception_does_not_raise(self) -> None:
        """An exception from the Azure SDK is caught and logged; no re-raise."""
        s = Settings(app_config_endpoint="https://example.azconfig.io")

        with patch(
            "azure.appconfiguration.AzureAppConfigurationClient"
        ) as MockClient, patch("azure.identity.DefaultAzureCredential"):
            MockClient.return_value.list_configuration_settings.side_effect = RuntimeError(
                "network error"
            )
            apply_app_configuration(s)  # must not raise
