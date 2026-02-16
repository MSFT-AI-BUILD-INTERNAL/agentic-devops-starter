# ============================================================================
# main.tf - Azure App Service Sidecar infrastructure
# Frontend(Nginx, Main) + Backend(FastAPI, Sidecar) container execution
# Sidecar mode: All containers share localhost network
# Same hostname → Same-Origin → No CORS restrictions (no wildcard * needed)
# ============================================================================

# ============================================================================
# Data Sources
# ============================================================================
data "azurerm_subscription" "current" {}

# ============================================================================
# Local Variables
# ============================================================================
locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  app_hostname    = "app-${local.resource_prefix}.azurewebsites.net"
  acr_server      = azurerm_container_registry.main.login_server

  # CORS: self domain + custom domain (if any)
  cors_origins = var.custom_domain != "" ? [
    "https://${local.app_hostname}",
    "https://${var.custom_domain}"
  ] : [
    "https://${local.app_hostname}"
  ]

  # FastAPI CORS_ORIGINS environment variable (comma-separated)
  cors_origins_csv = join(",", local.cors_origins)
}

# ============================================================================
# Resource Group
# ============================================================================
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = var.tags
}

# ============================================================================
# Log Analytics Workspace (Monitoring)
# ============================================================================
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = var.tags
}

# ============================================================================
# Azure Container Registry
# ============================================================================
resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.acr_sku
  admin_enabled       = true
  tags                = var.tags
}

# ============================================================================
# App Service Plan (Linux Containers)
# ============================================================================
resource "azurerm_service_plan" "main" {
  name                = "asp-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  tags                = var.tags
}

# ============================================================================
# Web App — Sidecar Container mode
#
# Architecture:
#   [Browser] → https://app-xxx.azurewebsites.net
#                        ↓
#               ┌─── frontend (Nginx:80, Main) ──┐
#               │  / → React SPA                 │
#               │  /api/ → localhost:5100         │
#               └────────────────────────────────┘
#                ↕ localhost shared
#               ┌─── backend (uvicorn:5100, Sidecar) ┐
#               │  FastAPI + AG-UI                   │
#               └────────────────────────────────────┘
#
# Sidecar mode: All containers share localhost
# Same hostname → Same-Origin → Browser doesn't perform CORS checks
# CORS allowed_origins = self domain only (no wildcard *)
# ============================================================================
resource "azurerm_linux_web_app" "main" {
  name                = "app-${local.resource_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true
  tags                = var.tags

  # Enable client certificate (optional)
  client_certificate_enabled = true
  client_certificate_mode    = "Optional"

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = var.always_on
    container_registry_use_managed_identity = true
    health_check_path                       = "/health"
    health_check_eviction_time_in_min       = 5

    # -------------------------------------------------------------------
    # CORS configuration (App Service level)
    # Same-Origin, so only allow self domain.
    # No wildcard (*) — explicit origins only.
    # -------------------------------------------------------------------
    cors {
      allowed_origins     = local.cors_origins
      support_credentials = false
    }

    # Security: minimum TLS 1.2
    minimum_tls_version = "1.2"

    # Disable remote debugging
    remote_debugging_enabled = false
  }

  app_settings = {
    # Sidecar mode: app_settings are injected into all containers (main + sidecar)
    # https://learn.microsoft.com/en-us/azure/app-service/tutorial-custom-container-sidecar
    # "App settings are accessible to all the containers in the app."
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"

    # Azure AI Configuration (optional)
    "AZURE_AI_PROJECT_ENDPOINT"      = var.azure_ai_project_endpoint
    "AZURE_AI_MODEL_DEPLOYMENT_NAME" = var.azure_ai_model_deployment_name

    # CORS — FastAPI level also restricts to self domain (defense in depth)
    "CORS_ORIGINS" = local.cors_origins_csv
  }

  logs {
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
    application_logs {
      file_system_level = "Information"
    }
  }

  lifecycle {
    ignore_changes = [
      site_config[0].application_stack,
    ]
  }
}

# ============================================================================
# Enable Sidecar mode (linuxFxVersion = "sitecontainers")
# ============================================================================
resource "azapi_update_resource" "sidecar_mode" {
  type        = "Microsoft.Web/sites@2024-04-01"
  resource_id = azurerm_linux_web_app.main.id

  body = {
    properties = {
      siteConfig = {
        linuxFxVersion = "sitecontainers"
      }
    }
  }

  depends_on = [azurerm_linux_web_app.main]
}

# ============================================================================
# Main Container — Frontend (Nginx + React SPA)
# isMain = true → receives external traffic
# ============================================================================
resource "azapi_resource" "container_frontend" {
  type      = "Microsoft.Web/sites/sitecontainers@2024-04-01"
  name      = "frontend"
  parent_id = azurerm_linux_web_app.main.id

  schema_validation_enabled = false

  body = {
    properties = {
      image      = "${local.acr_server}/${var.frontend_docker_image}:latest"
      isMain     = true
      targetPort = "80"
      authType   = "SystemIdentity"

      # Inherit app_settings as container environment variables
      inheritAppSettingsAndConnectionStrings = true
      environmentVariables                   = []
    }
  }

  depends_on = [azapi_update_resource.sidecar_mode, azurerm_role_assignment.acr_pull]
}

# ============================================================================
# Sidecar Container — Backend (FastAPI + AG-UI)
# isMain = false → sidecar, accessible via localhost:5100
#
# Important: inheritAppSettingsAndConnectionStrings = true
#   → app_settings (AZURE_AI_PROJECT_ENDPOINT, etc.) inherited as container env vars
# ============================================================================
resource "azapi_resource" "container_backend" {
  type      = "Microsoft.Web/sites/sitecontainers@2024-04-01"
  name      = "backend"
  parent_id = azurerm_linux_web_app.main.id

  schema_validation_enabled = false

  body = {
    properties = {
      image      = "${local.acr_server}/${var.backend_docker_image}:latest"
      isMain     = false
      targetPort = "5100"
      authType   = "SystemIdentity"

      # Inherit app_settings as container environment variables
      inheritAppSettingsAndConnectionStrings = true
      environmentVariables                   = []
    }
  }

  depends_on = [azapi_update_resource.sidecar_mode, azurerm_role_assignment.acr_pull]
}

# ============================================================================
# Custom Domain Binding (optional)
# ============================================================================
resource "azurerm_app_service_custom_hostname_binding" "main" {
  count               = var.custom_domain != "" ? 1 : 0
  hostname            = var.custom_domain
  app_service_name    = azurerm_linux_web_app.main.name
  resource_group_name = azurerm_resource_group.main.name
}

# ============================================================================
# ACR Role Assignment — Managed Identity → ACR Pull
# ============================================================================
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}

# ============================================================================
# Diagnostic Settings
# ============================================================================
resource "azurerm_monitor_diagnostic_setting" "main" {
  name                       = "diag-app"
  target_resource_id         = azurerm_linux_web_app.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AppServiceHTTPLogs"
  }

  enabled_log {
    category = "AppServiceConsoleLogs"
  }

  enabled_log {
    category = "AppServiceAppLogs"
  }

  metric {
    category = "AllMetrics"
  }
}
