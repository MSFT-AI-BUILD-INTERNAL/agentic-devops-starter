output "acr_id" {
  description = "The ID of the Azure Container Registry"
  value       = local.acr.id
}

output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = local.acr.name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry"
  value       = local.acr.login_server
}

output "acr_admin_username" {
  description = "The admin username for the Azure Container Registry"
  value       = try(local.acr.admin_username, null)
  sensitive   = true
}

output "acr_admin_password" {
  description = "The admin password for the Azure Container Registry"
  value       = try(local.acr.admin_password, null)
  sensitive   = true
}

output "acr_identity_principal_id" {
  description = "The principal ID of the managed identity (only populated when Terraform creates the ACR)"
  value       = try(azurerm_container_registry.acr[0].identity[0].principal_id, null)
}
