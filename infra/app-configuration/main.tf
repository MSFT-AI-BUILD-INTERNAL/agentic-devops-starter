resource "azurerm_app_configuration" "main" {
  name                = var.app_configuration_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  local_auth_enabled    = var.local_auth_enabled
  public_network_access = var.public_network_access

  tags = var.tags

  # NOTE: Private Endpoints, Private DNS zones and NSGs for this store are
  # intentionally NOT managed here - they are owned by a separate stack.
  lifecycle {
    prevent_destroy = true
  }
}
