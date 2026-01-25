output "app_gateway_id" {
  description = "ID of the Application Gateway"
  value       = azurerm_application_gateway.main.id
}

output "app_gateway_name" {
  description = "Name of the Application Gateway"
  value       = azurerm_application_gateway.main.name
}

output "app_gateway_public_ip" {
  description = "Public IP address of the Application Gateway"
  value       = azurerm_public_ip.appgw.ip_address
}

output "app_gateway_public_ip_id" {
  description = "ID of the Application Gateway public IP"
  value       = azurerm_public_ip.appgw.id
}

output "vnet_id" {
  description = "ID of the virtual network"
  value       = azurerm_virtual_network.appgw.id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.appgw.name
}

output "aks_subnet_id" {
  description = "ID of the AKS subnet"
  value       = azurerm_subnet.aks.id
}

output "appgw_subnet_id" {
  description = "ID of the Application Gateway subnet"
  value       = azurerm_subnet.appgw.id
}

output "agic_identity_id" {
  description = "ID of the AGIC managed identity"
  value       = azurerm_user_assigned_identity.agic.id
}

output "agic_identity_client_id" {
  description = "Client ID of the AGIC managed identity"
  value       = azurerm_user_assigned_identity.agic.client_id
}

output "agic_identity_principal_id" {
  description = "Principal ID of the AGIC managed identity"
  value       = azurerm_user_assigned_identity.agic.principal_id
}

output "appgw_identity_id" {
  description = "ID of the Application Gateway managed identity"
  value       = azurerm_user_assigned_identity.appgw.id
}

output "appgw_identity_principal_id" {
  description = "Principal ID of the Application Gateway managed identity"
  value       = azurerm_user_assigned_identity.appgw.principal_id
}

output "appgw_identity_client_id" {
  description = "Client ID of the Application Gateway managed identity"
  value       = azurerm_user_assigned_identity.appgw.client_id
}
