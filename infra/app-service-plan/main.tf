# Azure App Service Plan for hosting containers
resource "azurerm_service_plan" "main" {
  count               = var.create ? 1 : 0
  name                = var.service_plan_name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.tags
}

# When ``create = false``, reference the existing plan instead.
data "azurerm_service_plan" "existing" {
  count               = var.create ? 0 : 1
  name                = var.service_plan_name
  resource_group_name = var.resource_group_name
}

locals {
  plan = var.create ? azurerm_service_plan.main[0] : data.azurerm_service_plan.existing[0]
}
