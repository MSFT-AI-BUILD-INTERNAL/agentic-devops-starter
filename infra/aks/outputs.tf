output "aks_id" {
  description = "The ID of the Azure Kubernetes Service cluster"
  value       = azurerm_kubernetes_cluster.aks.id
}

output "aks_name" {
  description = "The name of the Azure Kubernetes Service cluster"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "aks_fqdn" {
  description = "The FQDN of the Azure Kubernetes Service cluster"
  value       = azurerm_kubernetes_cluster.aks.fqdn
}

output "aks_kube_config" {
  description = "Kubernetes configuration for connecting to the cluster"
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

output "aks_node_resource_group" {
  description = "The resource group containing AKS nodes"
  value       = azurerm_kubernetes_cluster.aks.node_resource_group
}

output "aks_kubelet_identity" {
  description = "The kubelet identity of the AKS cluster"
  value = {
    object_id = try(azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id, null)
    client_id = try(azurerm_kubernetes_cluster.aks.kubelet_identity[0].client_id, null)
  }
}

output "aks_identity_principal_id" {
  description = "The principal ID of the system assigned identity"
  value       = try(azurerm_kubernetes_cluster.aks.identity[0].principal_id, null)
}
