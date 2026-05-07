output "app_configuration_id" {
  description = "Resource ID of the Azure App Configuration store"
  value       = azurerm_app_configuration.main.id
}

output "app_configuration_name" {
  description = "Name of the Azure App Configuration store"
  value       = azurerm_app_configuration.main.name
}

output "app_configuration_endpoint" {
  description = "Endpoint URL of the Azure App Configuration store (use with DefaultAzureCredential)"
  value       = azurerm_app_configuration.main.endpoint
}

output "sample_feature_flag_name" {
  description = "Name of the sample feature flag seeded in the store"
  value       = azurerm_app_configuration_feature.sample.name
}
