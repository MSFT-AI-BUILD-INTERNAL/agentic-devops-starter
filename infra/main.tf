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

# Application Gateway Module
module "app_gateway" {
  source = "./app-gateway"

  app_gateway_name     = var.app_gateway_name
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  vnet_name            = var.vnet_name
  vnet_address_space   = var.vnet_address_space
  appgw_subnet_name    = var.appgw_subnet_name
  appgw_subnet_prefix  = var.appgw_subnet_prefix
  aks_subnet_name      = var.aks_subnet_name
  aks_subnet_prefix    = var.aks_subnet_prefix
  public_ip_name       = var.app_gateway_public_ip_name
  app_gateway_sku_name = var.app_gateway_sku_name
  app_gateway_sku_tier = var.app_gateway_sku_tier
  app_gateway_capacity = var.app_gateway_capacity
  waf_firewall_mode    = var.waf_firewall_mode
  subscription_id      = data.azurerm_subscription.current.subscription_id
  tags                 = var.tags

  depends_on = [azurerm_resource_group.main]
}

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

# Azure Kubernetes Service Module
module "aks" {
  source = "./aks"

  aks_cluster_name           = var.aks_cluster_name
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  dns_prefix                 = var.aks_dns_prefix
  kubernetes_version         = var.kubernetes_version
  node_count                 = var.node_count
  vm_size                    = var.vm_size
  enable_auto_scaling        = var.enable_auto_scaling
  min_node_count             = var.min_node_count
  max_node_count             = var.max_node_count
  aks_subnet_id              = module.app_gateway.aks_subnet_id
  app_gateway_id             = module.app_gateway.app_gateway_id
  acr_id                     = module.acr.acr_id
  log_analytics_workspace_id = module.log_analytics.workspace_id
  tags                       = var.tags

  depends_on = [azurerm_resource_group.main, module.acr, module.log_analytics, module.app_gateway]
}

# Managed Identity for Workload Identity
module "managed_identity" {
  source = "./managed-identity"

  identity_name        = "${var.aks_cluster_name}-workload-identity"
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  oidc_issuer_url      = module.aks.oidc_issuer_url
  kubernetes_namespace = "default"
  service_account_name = "agentic-devops-sa"
  tags                 = var.tags

  depends_on = [module.aks]
}
