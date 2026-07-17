"""Tests for Azure App Configuration integration in config loading."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import Settings, apply_app_configuration

_AC_MODULE = "azure.appconfiguration.AzureAppConfigurationClient"
_IDENTITY_MODULE = "azure.identity.DefaultAzureCredential"


def _make_ac_setting(key: str, value: str) -> MagicMock:
    """Return a mock ConfigurationSetting with key and value attributes."""
    s = MagicMock()
    s.key = key
    s.value = value
    return s


class TestApplyAppConfigurationNoop:
    """apply_app_configuration is a no-op when the endpoint is not configured."""

    def test_no_endpoint_does_not_call_azure(self) -> None:
        """When app_config_endpoint is empty, no Azure client is created."""
        s = Settings(app_config_endpoint="")

        with patch(_AC_MODULE) as mock_client_cls:
            apply_app_configuration(s)

        mock_client_cls.assert_not_called()

    def test_no_endpoint_settings_unchanged(self) -> None:
        """Fields retain their defaults when no endpoint is set."""
        s = Settings(app_config_endpoint="")
        original_endpoint = s.azure_ai_project_endpoint

        apply_app_configuration(s)

        assert s.azure_ai_project_endpoint == original_endpoint


class TestApplyAppConfigurationValues:
    """App Configuration values are applied when the endpoint is configured."""

    def test_ac_value_applied_when_no_env_var_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An App Configuration entry should be written to the matching settings field."""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("COPILOT_API_AZURE_AI_PROJECT_ENDPOINT", raising=False)

        ac_settings = [
            _make_ac_setting(
                "AZURE_AI_PROJECT_ENDPOINT",
                "https://my-foundry.services.ai.azure.com",
            )
        ]

        mock_client = MagicMock()
        mock_client.list_configuration_settings.return_value = iter(ac_settings)

        s = Settings(app_config_endpoint="https://my-appconfig.azconfig.io")

        with patch(_AC_MODULE, return_value=mock_client):
            with patch(_IDENTITY_MODULE):
                apply_app_configuration(s)

        assert s.azure_ai_project_endpoint == "https://my-foundry.services.ai.azure.com"

    def test_ac_label_passed_to_list_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The app_config_label is forwarded to list_configuration_settings."""
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
        monkeypatch.delenv("COPILOT_API_AZURE_AI_PROJECT_ENDPOINT", raising=False)

        mock_client = MagicMock()
        mock_client.list_configuration_settings.return_value = iter([])

        s = Settings(
            app_config_endpoint="https://my-appconfig.azconfig.io",
            app_config_label="production",
        )

        with patch(_AC_MODULE, return_value=mock_client):
            with patch(_IDENTITY_MODULE):
                apply_app_configuration(s)

        mock_client.list_configuration_settings.assert_called_once_with(
            label_filter="production"
        )

    def test_empty_label_passed_as_none(self) -> None:
        """An empty app_config_label results in label_filter=None."""
        mock_client = MagicMock()
        mock_client.list_configuration_settings.return_value = iter([])

        s = Settings(
            app_config_endpoint="https://my-appconfig.azconfig.io",
            app_config_label="",
        )

        with patch(_AC_MODULE, return_value=mock_client):
            with patch(_IDENTITY_MODULE):
                apply_app_configuration(s)

        mock_client.list_configuration_settings.assert_called_once_with(label_filter=None)


class TestApplyAppConfigurationEnvVarPrecedence:
    """Environment variables take precedence over App Configuration values."""

    def test_env_var_overrides_ac_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When an env var is explicitly set, the App Config value must not overwrite it."""
        env_value = "https://env-var-foundry.services.ai.azure.com"
        monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", env_value)

        ac_settings = [
            _make_ac_setting(
                "AZURE_AI_PROJECT_ENDPOINT",
                "https://app-config-foundry.services.ai.azure.com",
            )
        ]

        mock_client = MagicMock()
        mock_client.list_configuration_settings.return_value = iter(ac_settings)

        s = Settings(app_config_endpoint="https://my-appconfig.azconfig.io")

        with patch(_AC_MODULE, return_value=mock_client):
            with patch(_IDENTITY_MODULE):
                apply_app_configuration(s)

        assert s.azure_ai_project_endpoint == env_value

    def test_copilot_api_prefix_env_var_overrides_ac(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COPILOT_API_-prefixed env var also prevents App Config from overwriting."""
        env_value = "https://prefix-foundry.services.ai.azure.com"
        monkeypatch.setenv("COPILOT_API_AZURE_AI_PROJECT_ENDPOINT", env_value)
        monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)

        ac_settings = [
            _make_ac_setting(
                "AZURE_AI_PROJECT_ENDPOINT",
                "https://app-config-foundry.services.ai.azure.com",
            )
        ]

        mock_client = MagicMock()
        mock_client.list_configuration_settings.return_value = iter(ac_settings)

        s = Settings(app_config_endpoint="https://my-appconfig.azconfig.io")

        with patch(_AC_MODULE, return_value=mock_client):
            with patch(_IDENTITY_MODULE):
                apply_app_configuration(s)

        assert s.azure_ai_project_endpoint == env_value

    def test_azure_client_error_does_not_raise(self) -> None:
        """A failure in Azure App Configuration loading must not propagate as an exception."""
        mock_client = MagicMock()
        mock_client.list_configuration_settings.side_effect = RuntimeError("network error")

        s = Settings(app_config_endpoint="https://my-appconfig.azconfig.io")

        with patch(_AC_MODULE, return_value=mock_client):
            with patch(_IDENTITY_MODULE):
                apply_app_configuration(s)  # must not raise

        assert s.azure_ai_project_endpoint == ""

