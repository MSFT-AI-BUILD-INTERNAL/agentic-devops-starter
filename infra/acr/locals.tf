locals {
  acr = var.create ? azurerm_container_registry.acr[0] : data.azurerm_container_registry.existing[0]
}
