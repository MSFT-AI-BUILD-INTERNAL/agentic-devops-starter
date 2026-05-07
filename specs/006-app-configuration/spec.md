# Feature Specification: Azure App Configuration Integration

**Feature ID**: 006-app-configuration
**Date**: 2026-05-07
**Status**: Implementation

## Overview

Integrate **Azure App Configuration** as the centralized store for
application settings and feature flags. Provision the resource via
Terraform, grant the App Service managed identity read access using
RBAC, and expose a thin async helper plus a sample HTTP endpoint that
reads a feature flag from the configuration store.

## Background

Application settings are currently scattered between Terraform
`app_settings` (`infra/main.tf`) and CI-injected secrets
(`.github/workflows/deploy.yml`). Azure App Configuration provides a
managed, central source of truth for non-secret configuration and
first-class **feature flags** with built-in rollout/targeting support
([Microsoft docs](https://learn.microsoft.com/en-us/azure/azure-app-configuration/overview)).

## Goals

1. Provision `Microsoft.AppConfiguration/configurationStores` (Standard
   SKU, required for feature flags) via a new Terraform module.
2. Seed a sample feature flag (`Beta`) via Terraform so the deployment
   is self-contained and reproducible.
3. Grant the App Service system-assigned managed identity the
   **App Configuration Data Reader** role on the store so the backend
   can read flags using `DefaultAzureCredential` — no connection
   strings or shared keys committed to source.
4. Expose `AZURE_APPCONFIG_ENDPOINT` to the backend via App Service
   app settings so the application can locate the store.
5. Add a thin Python helper (`app/feature_flags.py`) and a sample
   `GET /feature-flags/{name}` endpoint that returns whether a feature
   flag is enabled.

## Non-Goals

- Migrating *all* existing app settings into App Configuration.
- Targeting / percentage rollout filters on the sample flag (the
  framework supports them; we ship a simple boolean flag for clarity).
- A dedicated frontend toggle UI.

## Architecture

```
+------------------+        AAD token         +----------------------+
| Azure App Service|  ----------------------> | Azure App Config     |
| (System MI)      |    DefaultAzureCredential|  - Beta (feature)    |
|  agui_server.py  |                          +----------------------+
|   feature_flags  |
+------------------+
```

### Terraform

- New module `infra/app-configuration/` with:
  - `azurerm_app_configuration` (Standard SKU, local auth disabled,
    public network enabled for parity with current ACR/App Service).
  - `azurerm_app_configuration_feature` for the sample `Beta` flag.
- `infra/main.tf` adds:
  - Module instantiation.
  - `azurerm_role_assignment` granting the App Service MI
    **App Configuration Data Reader** on the store.
  - `AZURE_APPCONFIG_ENDPOINT` injected into App Service app settings.
- New variables for the store name and the sample flag's default.
- New output for the App Configuration endpoint.

### Backend

- Add `azure-appconfiguration>=1.8.0` to `app/pyproject.toml`.
- Add `app/feature_flags.py`:
  - `is_feature_enabled(name: str, *, default: bool = False) -> bool`
  - Async function using
    `azure.appconfiguration.aio.AzureAppConfigurationClient` with
    `DefaultAzureCredential`.
  - Returns `default` (logged at INFO) when
    `AZURE_APPCONFIG_ENDPOINT` is unset (local dev / unit tests).
  - Returns `default` (logged at WARNING with context) on
    `ResourceNotFoundError` (flag not yet seeded). Other exceptions
    propagate so they are not silently swallowed
    (per `code-review-criteria` §4).
- Add `GET /feature-flags/{name}` endpoint to `app/agui_server.py`
  returning `{"name": str, "enabled": bool}`.
- `app/.env.example` documents `AZURE_APPCONFIG_ENDPOINT`.

### Tests

- `tests/test_feature_flags.py`:
  - `is_feature_enabled` returns `default` when endpoint env unset.
  - `is_feature_enabled` honours an enabled flag from a mocked client.
  - `is_feature_enabled` honours a disabled flag from a mocked client.
- `tests/test_agui_server.py`:
  - `GET /feature-flags/{name}` returns the helper's result with HTTP
    200 when endpoint env is unset (default `False`).

## Risks / Mitigations

- **Cold-start latency.** Each call constructs an
  `AzureAppConfigurationClient`. The sample endpoint is intended for
  demonstration; production callers should cache or use the
  `azure-appconfiguration-provider` refresh client. Documented in
  `feature_flags.py` docstring.
- **Permission propagation.** Azure RBAC role assignments can take a
  few minutes to propagate after `terraform apply`; the helper logs a
  clear `Forbidden` message rather than crashing the request.

## Acceptance Criteria

1. `terraform plan` shows exactly one new App Configuration store, one
   feature flag, and one role assignment when run against a fresh
   state.
2. `uv run pytest tests/ -v` passes including the new feature-flag
   tests.
3. Calling `GET /feature-flags/Beta` against a deployed App Service
   returns `{"name": "Beta", "enabled": true}` once the Terraform
   default of `enabled = true` has been applied.
