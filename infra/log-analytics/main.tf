resource "azurerm_log_analytics_workspace" "aks" {
  count               = var.create ? 1 : 0
  name                = var.log_analytics_workspace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku
  retention_in_days   = var.retention_in_days

  tags = var.tags
}

# When ``create = false``, reference the existing workspace instead.
data "azurerm_log_analytics_workspace" "existing" {
  count               = var.create ? 0 : 1
  name                = var.log_analytics_workspace_name
  resource_group_name = var.resource_group_name
}

locals {
  workspace = var.create ? azurerm_log_analytics_workspace.aks[0] : data.azurerm_log_analytics_workspace.existing[0]
}

# The Container Insights solution is only created together with the workspace.
# When referencing an existing workspace, assume the solution is already in
# place (or unneeded for App-Service-only deployments).
resource "azurerm_log_analytics_solution" "container_insights" {
  count                 = var.create ? 1 : 0
  solution_name         = "ContainerInsights"
  location              = var.location
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.aks[0].id
  workspace_name        = azurerm_log_analytics_workspace.aks[0].name

  plan {
    publisher = "Microsoft"
    product   = "OMSGallery/ContainerInsights"
  }

  tags = var.tags

  depends_on = [azurerm_log_analytics_workspace.aks]
}
