output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

output "acr_id" {
  description = "The ID of the Azure Container Registry"
  value       = module.acr.acr_id
}

output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = module.acr.acr_name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry"
  value       = module.acr.acr_login_server
}

output "aks_id" {
  description = "The ID of the Azure Kubernetes Service cluster"
  value       = module.aks.aks_id
}

output "aks_name" {
  description = "The name of the Azure Kubernetes Service cluster"
  value       = module.aks.aks_name
}

output "aks_fqdn" {
  description = "The FQDN of the Azure Kubernetes Service cluster"
  value       = module.aks.aks_fqdn
}

output "aks_node_resource_group" {
  description = "The resource group containing AKS nodes"
  value       = module.aks.aks_node_resource_group
}

output "configure_kubectl_command" {
  description = "Command to configure kubectl to connect to the AKS cluster"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${module.aks.aks_name}"
}
