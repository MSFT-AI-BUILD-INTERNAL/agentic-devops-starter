output "app_configuration_id" {
  description = "ID of the App Configuration store"
  value       = azurerm_app_configuration.main.id
}

output "app_configuration_name" {
  description = "Name of the App Configuration store"
  value       = azurerm_app_configuration.main.name
}

output "app_configuration_endpoint" {
  description = "Endpoint URL of the App Configuration store"
  value       = azurerm_app_configuration.main.endpoint
}
