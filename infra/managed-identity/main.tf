# Managed Identity for AKS workload pods to access Azure resources
resource "azurerm_user_assigned_identity" "aks_workload" {
  name                = var.identity_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# Federated identity credential for Kubernetes service account
resource "azurerm_federated_identity_credential" "aks_workload" {
  name                = "${var.identity_name}-federated-credential"
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.aks_workload.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = var.oidc_issuer_url
  subject             = "system:serviceaccount:${var.kubernetes_namespace}:${var.service_account_name}"
}
