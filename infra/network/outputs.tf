output "vnet_id" {
  description = "ID of the virtual network"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.main.name
}

output "app_integration_subnet_id" {
  description = "ID of the App Service integration subnet"
  value       = azurerm_subnet.app_integration.id
}

output "private_endpoint_subnet_id" {
  description = "ID of the private endpoint subnet"
  value       = azurerm_subnet.private_endpoints.id
}
