output "acr_id" {
  description = "The ID of the Azure Container Registry"
  value       = azurerm_container_registry.acr.id
}

output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  description = "The admin username for the Azure Container Registry"
  value       = azurerm_container_registry.acr.admin_username
  sensitive   = true
}

output "acr_admin_password" {
  description = "The admin password for the Azure Container Registry"
  value       = azurerm_container_registry.acr.admin_password
  sensitive   = true
}

output "acr_identity_principal_id" {
  description = "The principal ID of the managed identity"
  value       = try(azurerm_container_registry.acr.identity[0].principal_id, null)
}
