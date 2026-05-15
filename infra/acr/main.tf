resource "azurerm_container_registry" "acr" {
  count               = var.create ? 1 : 0
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = var.admin_enabled

  public_network_access_enabled = var.public_network_access_enabled

  dynamic "identity" {
    for_each = var.identity_type != null ? [1] : []
    content {
      type = var.identity_type
    }
  }

  tags = var.tags
}

# When ``create = false``, reference the pre-existing ACR so downstream
# modules (App Service, deploy pipelines) can still consume its outputs.
data "azurerm_container_registry" "existing" {
  count               = var.create ? 0 : 1
  name                = var.acr_name
  resource_group_name = var.resource_group_name
}
