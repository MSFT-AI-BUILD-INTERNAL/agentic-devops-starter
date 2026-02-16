# Azure App Service Plan for hosting containers
resource "azurerm_service_plan" "main" {
  name                = var.service_plan_name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.tags
}
