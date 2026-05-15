# Output values from infrastructure provisioning

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

# Azure Container Registry
output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = module.acr.acr_name
}

output "acr_id" {
  description = "ID of the Azure Container Registry"
  value       = module.acr.acr_id
}

output "acr_login_server" {
  description = "Login server URL for the Azure Container Registry"
  value       = module.acr.acr_login_server
}

# App Service Plan
output "app_service_plan_id" {
  description = "ID of the App Service Plan"
  value       = module.app_service_plan.service_plan_id
}

output "app_service_plan_name" {
  description = "Name of the App Service Plan"
  value       = module.app_service_plan.service_plan_name
}

# App Service
output "app_service_name" {
  description = "Name of the App Service"
  value       = module.app_service.app_service_name
}

output "app_service_default_hostname" {
  description = "Default hostname of the App Service (access URL)"
  value       = module.app_service.app_service_default_hostname
}

output "app_service_url" {
  description = "HTTPS URL of the App Service"
  value       = "https://${module.app_service.app_service_default_hostname}"
}

output "app_service_identity_principal_id" {
  description = "Principal ID of the App Service managed identity"
  value       = module.app_service.app_service_identity_principal_id
}

# Log Analytics
output "log_analytics_workspace_id" {
  description = "ID of the Log Analytics Workspace"
  value       = module.log_analytics.workspace_id
}

output "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace"
  value       = module.log_analytics.workspace_name
}

# Storage Account
output "storage_account_name" {
  description = "Name of the Storage Account"
  value       = module.storage.storage_account_name
}

output "storage_account_id" {
  description = "ID of the Storage Account"
  value       = module.storage.storage_account_id
}

output "storage_primary_blob_endpoint" {
  description = "Primary blob endpoint URL of the Storage Account"
  value       = module.storage.primary_blob_endpoint
}

# Network
output "vnet_id" {
  description = "ID of the virtual network"
  value       = module.network.vnet_id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = module.network.vnet_name
}

output "blob_private_endpoint_ip" {
  description = "Private IP address of the Blob Storage private endpoint"
  value       = azurerm_private_endpoint.blob.private_service_connection[0].private_ip_address
}
