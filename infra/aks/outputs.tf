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

output "oidc_issuer_url" {
  description = "The OIDC issuer URL for Workload Identity"
  value       = azurerm_kubernetes_cluster.aks.oidc_issuer_url
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

# AGIC Identity (created by AKS addon)
output "agic_identity_principal_id" {
  description = "The principal ID of the AGIC identity created by AKS addon"
  value       = try(azurerm_kubernetes_cluster.aks.ingress_application_gateway[0].ingress_application_gateway_identity[0].object_id, null)
}

output "agic_identity_object_id" {
  description = "The object ID of the AGIC identity created by AKS addon (same as principal_id)"
  value       = try(azurerm_kubernetes_cluster.aks.ingress_application_gateway[0].ingress_application_gateway_identity[0].object_id, null)
}

output "agic_identity_client_id" {
  description = "The client ID of the AGIC identity created by AKS addon"
  value       = try(azurerm_kubernetes_cluster.aks.ingress_application_gateway[0].ingress_application_gateway_identity[0].client_id, null)
}
