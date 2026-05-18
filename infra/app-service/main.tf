# Azure App Service with multi-container (sidecar) support
resource "azurerm_linux_web_app" "main" {
  name                = var.app_service_name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = var.service_plan_id

  https_only                = true
  virtual_network_subnet_id = var.virtual_network_subnet_id

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

  lifecycle {
    # app_settings is a full-replace map — Terraform would delete keys set
    # externally (e.g. GITHUB_TOKEN set by deploy.yml). Ignore after initial
    # creation so both Terraform and deploy workflow can coexist.
    ignore_changes = [app_settings]
  }
}
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                     = azurerm_linux_web_app.main.identity[0].principal_id
  role_definition_name             = "AcrPull"
  scope                            = var.acr_id
  skip_service_principal_aad_check = true

  depends_on = [azurerm_linux_web_app.main]

  lifecycle {
    ignore_changes = all
  }
}

# Role assignment: Azure AI Developer on AI Foundry for App Service Identity
resource "azurerm_role_assignment" "ai_developer" {
  count                            = var.ai_foundry_resource_id != "" ? 1 : 0
  principal_id                     = azurerm_linux_web_app.main.identity[0].principal_id
  role_definition_name             = "Azure AI Developer"
  scope                            = var.ai_foundry_resource_id
  skip_service_principal_aad_check = true

  depends_on = [azurerm_linux_web_app.main]
}

# Role assignment: Cognitive Services User on AI Foundry
resource "azurerm_role_assignment" "cognitive_services_user" {
  count                            = var.ai_foundry_resource_id != "" ? 1 : 0
  principal_id                     = azurerm_linux_web_app.main.identity[0].principal_id
  role_definition_name             = "Cognitive Services User"
  scope                            = var.ai_foundry_resource_id
  skip_service_principal_aad_check = true

  depends_on = [azurerm_linux_web_app.main]
}
