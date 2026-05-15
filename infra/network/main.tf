# Virtual network for App Service VNet integration and private endpoints.
# Two delegated subnets are created:
#   - app_integration_subnet: delegated to Microsoft.Web/serverFarms for
#     regional VNet integration of the Linux Web App.
#   - private_endpoint_subnet: hosts private endpoints (e.g. for Blob Storage).
resource "azurerm_virtual_network" "main" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.vnet_address_space]

  tags = var.tags
}

resource "azurerm_subnet" "app_integration" {
  name                 = var.app_integration_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.app_integration_subnet_prefix]

  delegation {
    name = "appservice-delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "private_endpoint" {
  name                                          = var.private_endpoint_subnet_name
  resource_group_name                           = var.resource_group_name
  virtual_network_name                          = azurerm_virtual_network.main.name
  address_prefixes                              = [var.private_endpoint_subnet_prefix]
  private_endpoint_network_policies_enabled     = false
}
