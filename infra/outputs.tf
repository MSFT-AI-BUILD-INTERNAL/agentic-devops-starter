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

# Azure App Configuration
output "app_configuration_name" {
  description = "Name of the Azure App Configuration store"
  value       = module.app_configuration.app_configuration_name
}

output "app_configuration_endpoint" {
  description = "Endpoint URL of the Azure App Configuration store"
  value       = module.app_configuration.app_configuration_endpoint
}

output "app_configuration_sample_feature_flag" {
  description = "Name of the seeded sample feature flag"
  value       = module.app_configuration.sample_feature_flag_name
}
