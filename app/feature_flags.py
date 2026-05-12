"""Azure App Configuration helpers.

Thin async helper for reading **feature flags** from an Azure App
Configuration store. The store endpoint is read from
``AZURE_APPCONFIG_ENDPOINT`` and authentication uses
``DefaultAzureCredential`` (the App Service system-assigned managed
identity in production, developer credentials locally).

Centralized configuration enables operators to flip features at
runtime without redeploying the application
(https://learn.microsoft.com/en-us/azure/azure-app-configuration/overview).

Production callers that read feature flags on a hot path should use
the ``azure-appconfiguration-provider`` refresh client to cache
values. This helper opens a fresh client per call, which is fine for
the sample ``GET /feature-flags/{name}`` endpoint and demos but is
not optimised for high-throughput evaluation.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from azure.appconfiguration.aio import AzureAppConfigurationClient
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Azure App Configuration represents feature flags as configuration
# settings whose key is prefixed with this reserved namespace and whose
# content type carries the feature-flag content type.
# https://learn.microsoft.com/en-us/azure/azure-app-configuration/concept-feature-management
_FEATURE_FLAG_KEY_PREFIX = ".appconfig.featureflag/"


def _endpoint() -> str | None:
    """Return the configured App Configuration endpoint, or None if unset."""
    endpoint = os.environ.get("AZURE_APPCONFIG_ENDPOINT")
    return endpoint or None


async def is_feature_enabled(name: str, *, default: bool = False) -> bool:
    """Return whether the named feature flag is enabled.

    Falls back to ``default`` (with a log entry) when the App
    Configuration endpoint is not configured (e.g. local development)
    or when the named flag does not yet exist in the store. Other
    errors propagate so that misconfigurations are not silently
    swallowed.
    """
    endpoint = _endpoint()
    if endpoint is None:
        logger.info(
            "AZURE_APPCONFIG_ENDPOINT not set; returning default=%s for feature %r",
            default,
            name,
        )
        return default

    key = f"{_FEATURE_FLAG_KEY_PREFIX}{name}"
    credential = DefaultAzureCredential()
    try:
        async with AzureAppConfigurationClient(
            base_url=endpoint, credential=credential
        ) as client:
            try:
                setting = await client.get_configuration_setting(key=key)
            except ResourceNotFoundError:
                logger.warning(
                    "Feature flag %r not found in App Configuration; returning default=%s",
                    name,
                    default,
                )
                return default
    finally:
        await credential.close()

    if setting is None:
        logger.warning(
            "Feature flag %r returned no setting; returning default=%s", name, default
        )
        return default

    return _parse_feature_flag_enabled(setting.value, default=default)


def _parse_feature_flag_enabled(raw_value: str | None, *, default: bool) -> bool:
    """Parse the JSON payload of a feature-flag configuration setting."""
    if not raw_value:
        return default
    try:
        payload: Any = json.loads(raw_value)
    except json.JSONDecodeError:
        logger.warning(
            "Feature flag value is not valid JSON; returning default=%s. value=%r",
            default,
            raw_value,
        )
        return default

    if not isinstance(payload, dict):
        return default

    enabled = payload.get("enabled", default)
    return bool(enabled)
