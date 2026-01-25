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

# Virtual Network Module
module "vnet" {
  source = "./vnet"

  vnet_name                     = var.vnet_name
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  address_space                 = var.vnet_address_space
  aks_subnet_name               = var.aks_subnet_name
  aks_subnet_address_prefixes   = var.aks_subnet_address_prefixes
  appgw_subnet_name             = var.appgw_subnet_name
  appgw_subnet_address_prefixes = var.appgw_subnet_address_prefixes
  tags                          = var.tags

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
  vnet_subnet_id             = module.vnet.aks_subnet_id
  acr_id                     = module.acr.acr_id
  log_analytics_workspace_id = module.log_analytics.workspace_id
  tags                       = var.tags

  depends_on = [azurerm_resource_group.main, module.acr, module.log_analytics, module.vnet]
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

# Application Gateway Module
module "application_gateway" {
  source = "./application-gateway"

  appgw_name          = var.appgw_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  subnet_id           = module.vnet.appgw_subnet_id
  public_ip_name      = "${var.appgw_name}-pip"
  sku_name            = var.appgw_sku_name
  sku_tier            = var.appgw_sku_tier
  capacity            = var.appgw_capacity
  backend_fqdns       = var.appgw_backend_fqdns
  tags                = var.tags

  depends_on = [module.vnet, module.aks]
}
