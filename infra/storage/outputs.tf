output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "primary_blob_endpoint" {
  description = "Primary blob endpoint URL of the storage account"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "uploads_container_name" {
  description = "Name of the uploads blob container"
  value       = azurerm_storage_container.uploads.name
}

output "private_endpoint_id" {
  description = "ID of the blob private endpoint"
  value       = azurerm_private_endpoint.blob.id
}
