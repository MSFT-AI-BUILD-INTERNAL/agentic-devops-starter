terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Data source to get current subscription
data "azurerm_subscription" "current" {
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Log Analytics Module
module "log_analytics" {
  source = "./log-analytics"

  log_analytics_workspace_name = var.log_analytics_workspace_name
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  sku                          = var.log_analytics_sku
  retention_in_days            = var.log_analytics_retention_days
  tags                         = var.tags

  depends_on = [azurerm_resource_group.main]
}

# Network Module - Removed for App Service migration
# Virtual networks are not required for App Service
# module "network" {
#   source = "./network"
#
#   vnet_name            = var.vnet_name
#   resource_group_name  = azurerm_resource_group.main.name
#   location             = azurerm_resource_group.main.location
#   vnet_address_space   = var.vnet_address_space
#   aks_subnet_name      = var.aks_subnet_name
#   aks_subnet_prefix    = var.aks_subnet_prefix
#   tags                 = var.tags
#
#   depends_on = [azurerm_resource_group.main]
# }

# Azure Container Registry Module
module "acr" {
  source = "./acr"

  acr_name            = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.acr_sku
  admin_enabled       = var.acr_admin_enabled
  tags                = var.tags

  depends_on = [azurerm_resource_group.main]
}

# Azure Kubernetes Service Module - Removed for App Service migration
# module "aks" {
#   source = "./aks"
#
#   aks_cluster_name           = var.aks_cluster_name
#   resource_group_name        = azurerm_resource_group.main.name
#   location                   = azurerm_resource_group.main.location
#   dns_prefix                 = var.aks_dns_prefix
#   kubernetes_version         = var.kubernetes_version
#   node_count                 = var.node_count
#   vm_size                    = var.vm_size
#   enable_auto_scaling        = var.enable_auto_scaling
#   min_node_count             = var.min_node_count
#   max_node_count             = var.max_node_count
#   aks_subnet_id              = module.network.aks_subnet_id
#   acr_id                     = module.acr.acr_id
#   log_analytics_workspace_id = module.log_analytics.workspace_id
#   tags                       = var.tags
#
#   depends_on = [azurerm_resource_group.main, module.acr, module.log_analytics, module.network]
# }

# Managed Identity for Workload Identity - Removed for App Service migration
# App Service uses System-Assigned Managed Identity instead
# module "managed_identity" {
#   source = "./managed-identity"
#
#   identity_name        = "${var.aks_cluster_name}-workload-identity"
#   resource_group_name  = azurerm_resource_group.main.name
#   location             = azurerm_resource_group.main.location
#   oidc_issuer_url      = module.aks.oidc_issuer_url
#   kubernetes_namespace = "default"
#   service_account_name = "agentic-devops-sa"
#   tags                 = var.tags
#
#   depends_on = [module.aks]
# }
#
# # Role assignment: Azure AI Developer on AI Foundry for Workload Identity
# resource "azurerm_role_assignment" "workload_identity_ai_developer" {
#   count                            = var.ai_foundry_resource_id != "" ? 1 : 0
#   principal_id                     = module.managed_identity.identity_principal_id
#   role_definition_name             = "Azure AI Developer"
#   scope                            = var.ai_foundry_resource_id
#   skip_service_principal_aad_check = true
#
#   depends_on = [module.managed_identity]
# }
#
# # Role assignment: Cognitive Services User on AI Foundry for Agents API data actions
# resource "azurerm_role_assignment" "workload_identity_cognitive_services_user" {
#   count                            = var.ai_foundry_resource_id != "" ? 1 : 0
#   principal_id                     = module.managed_identity.identity_principal_id
#   role_definition_name             = "Cognitive Services User"
#   scope                            = var.ai_foundry_resource_id
#   skip_service_principal_aad_check = true
#
#   depends_on = [module.managed_identity]
# }

# Azure App Configuration Module
module "app_configuration" {
  source = "./app-configuration"

  app_configuration_name      = var.app_configuration_name
  resource_group_name         = azurerm_resource_group.main.name
  location                    = azurerm_resource_group.main.location
  sku                         = var.app_configuration_sku
  sample_feature_flag_name    = var.app_configuration_sample_feature_flag_name
  sample_feature_flag_enabled = var.app_configuration_sample_feature_flag_enabled
  tags                        = var.tags

  depends_on = [azurerm_resource_group.main]
}

# App Service Plan Module
module "app_service_plan" {
  source = "./app-service-plan"

  service_plan_name   = var.app_service_plan_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku_name            = var.app_service_plan_sku
  tags                = var.tags

  depends_on = [azurerm_resource_group.main]
}

# App Service Module
module "app_service" {
  source = "./app-service"

  app_service_name       = var.app_service_name
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  service_plan_id        = module.app_service_plan.service_plan_id
  sku_name               = var.app_service_plan_sku
  docker_registry_url    = "https://${module.acr.acr_login_server}"
  docker_image_name      = var.backend_image_name
  docker_image_tag       = "latest"
  acr_id                 = module.acr.acr_id
  ai_foundry_resource_id = var.ai_foundry_resource_id

  app_settings = {
    "AZURE_TENANT_ID"                = data.azurerm_subscription.current.tenant_id
    "AZURE_AI_PROJECT_ENDPOINT"      = var.azure_ai_project_endpoint
    "AZURE_AI_MODEL_DEPLOYMENT_NAME" = var.azure_ai_model_deployment_name
    "AZURE_OPENAI_API_VERSION"       = var.azure_openai_api_version
    "AZURE_APPCONFIG_ENDPOINT"       = module.app_configuration.app_configuration_endpoint
  }

  tags = var.tags

  depends_on = [azurerm_resource_group.main, module.acr, module.app_service_plan]
}

# Grant the App Service managed identity read access to App Configuration.
# Done in the root module rather than the app-configuration module to avoid a
# circular dependency between the two modules (app_service depends on the
# config endpoint, and the role assignment depends on the app_service identity).
resource "azurerm_role_assignment" "app_service_appconfig_data_reader" {
  principal_id                     = module.app_service.app_service_identity_principal_id
  role_definition_name             = "App Configuration Data Reader"
  scope                            = module.app_configuration.app_configuration_id
  skip_service_principal_aad_check = true

  depends_on = [module.app_service, module.app_configuration]
}
