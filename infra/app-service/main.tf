# Azure App Service with multi-container (sidecar) support
resource "azurerm_linux_web_app" "main" {
  name                = var.app_service_name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = var.service_plan_id

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = false
    container_registry_use_managed_identity = true

    # Container image configuration
    # docker_image_name includes tag (e.g., "myimage:latest")
    # docker_registry_url is the ACR URL (e.g., "https://myacr.azurecr.io")
    application_stack {
      docker_registry_url = var.docker_registry_url
      docker_image_name   = "${var.docker_image_name}:${var.docker_image_tag}"
    }

    # CORS managed here as single source of truth (not in deploy.yml)
    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
  }

  # Application settings (environment variables)
  app_settings = merge(
    {
      "WEBSITES_PORT"                       = "8080" # nginx listens on 8080
      "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
      "DOCKER_ENABLE_CI"                    = "true"
      "DOCKER_REGISTRY_SERVER_URL"          = var.docker_registry_url
    },
    var.app_settings
  )

  logs {
    application_logs {
      file_system_level = "Information"
    }

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }

  tags = var.tags
}

# Regional VNet integration so the App Service can reach private endpoints
# (e.g. the Blob Storage private endpoint). ``count`` is driven by a static
# boolean so Terraform can resolve it at plan time even when the subnet ID
# is the unknown output of another module.
resource "azurerm_app_service_virtual_network_swift_connection" "main" {
  count          = var.enable_vnet_integration ? 1 : 0
  app_service_id = azurerm_linux_web_app.main.id
  subnet_id      = var.vnet_integration_subnet_id

  depends_on = [azurerm_linux_web_app.main]
}

# Role assignments (AcrPull, Azure AI Developer, Cognitive Services User,
# Storage Blob Data Contributor) are intentionally NOT managed by Terraform.
# They are granted out-of-band by a privileged operator after the App Service
# managed identity exists. See DEPLOYMENT.md ("Manual role assignments") for
# the exact `az role assignment create` commands.
