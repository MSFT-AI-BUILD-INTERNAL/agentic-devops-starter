output "identity_client_id" {
  description = "Client ID of the managed identity"
  value       = azurerm_user_assigned_identity.aks_workload.client_id
}

output "identity_principal_id" {
  description = "Principal ID of the managed identity"
  value       = azurerm_user_assigned_identity.aks_workload.principal_id
}

output "identity_id" {
  description = "Resource ID of the managed identity"
  value       = azurerm_user_assigned_identity.aks_workload.id
}
