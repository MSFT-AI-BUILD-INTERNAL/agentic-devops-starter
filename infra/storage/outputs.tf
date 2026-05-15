output "storage_account_id" {
  description = "ID of the Storage Account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "Name of the Storage Account"
  value       = azurerm_storage_account.main.name
}

output "primary_blob_endpoint" {
  description = "Primary blob service endpoint URL"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "storage_account_identity_principal_id" {
  description = "Principal ID of the Storage Account managed identity (null if no identity)"
  value       = try(azurerm_storage_account.main.identity[0].principal_id, null)
}
