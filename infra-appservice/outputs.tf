# ============================================================================
# outputs.tf - Important information output after deployment
# Sidecar App Service configuration (Frontend=Main + Backend=Sidecar)
# ============================================================================

# ============================================================================
# Resource Group
# ============================================================================
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

# ============================================================================
# ACR
# ============================================================================
output "acr_name" {
  description = "Azure Container Registry name"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.main.login_server
}

# ============================================================================
# App Service
# ============================================================================
output "app_service_plan_name" {
  description = "App Service Plan name"
  value       = azurerm_service_plan.main.name
}

output "app_url" {
  description = "Application URL (Frontend + Backend on same origin)"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "webapp_name" {
  description = "Web App name"
  value       = azurerm_linux_web_app.main.name
}

output "cors_allowed_origins" {
  description = "CORS allowed origins (restrictive)"
  value       = local.cors_origins
}

# ============================================================================
# Managed Identity
# ============================================================================
output "identity_principal_id" {
  description = "Managed Identity Principal ID"
  value       = azurerm_linux_web_app.main.identity[0].principal_id
}

# ============================================================================
# Monitoring
# ============================================================================
output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

# ============================================================================
# Useful Commands
# ============================================================================
output "acr_login_command" {
  description = "Command to login to ACR"
  value       = "az acr login --name ${azurerm_container_registry.main.name}"
}

output "app_logs_command" {
  description = "Command to stream application logs"
  value       = "az webapp log tail --name ${azurerm_linux_web_app.main.name} --resource-group ${azurerm_resource_group.main.name}"
}

output "app_restart_command" {
  description = "Command to restart the application"
  value       = "az webapp restart --name ${azurerm_linux_web_app.main.name} --resource-group ${azurerm_resource_group.main.name}"
}
