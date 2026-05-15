output "workspace_id" {
  description = "The ID of the Log Analytics Workspace"
  value       = local.workspace.id
}

output "workspace_name" {
  description = "The name of the Log Analytics Workspace"
  value       = local.workspace.name
}

output "workspace_primary_shared_key" {
  description = "The primary shared key for the Log Analytics Workspace"
  value       = local.workspace.primary_shared_key
  sensitive   = true
}

output "container_insights_solution_id" {
  description = "The ID of the Container Insights solution (only populated when Terraform creates the workspace)"
  value       = try(azurerm_log_analytics_solution.container_insights[0].id, null)
}
