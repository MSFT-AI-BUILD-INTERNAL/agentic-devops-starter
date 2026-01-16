output "workspace_id" {
  description = "The ID of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.aks.id
}

output "workspace_name" {
  description = "The name of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.aks.name
}

output "workspace_resource_id" {
  description = "The resource ID of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.aks.id
}

output "workspace_primary_shared_key" {
  description = "The primary shared key for the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.aks.primary_shared_key
  sensitive   = true
}

output "container_insights_solution_id" {
  description = "The ID of the Container Insights solution"
  value       = azurerm_log_analytics_solution.container_insights.id
}
