resource "azurerm_virtual_network" "main" {
  name                = var.vnet_name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.address_space]
  tags                = var.tags

  lifecycle {
    prevent_destroy = true
  }
}

# Subnet for App Service VNet integration (outbound traffic)
resource "azurerm_subnet" "app_integration" {
  name                            = var.app_integration_subnet_name
  resource_group_name             = var.resource_group_name
  virtual_network_name            = azurerm_virtual_network.main.name
  address_prefixes                = [var.app_integration_subnet_prefix]
  default_outbound_access_enabled = false

  delegation {
    name = "app-service-delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [delegation]
  }
}

# Subnet for private endpoints
resource "azurerm_subnet" "private_endpoints" {
  name                              = var.private_endpoint_subnet_name
  resource_group_name               = var.resource_group_name
  virtual_network_name              = azurerm_virtual_network.main.name
  address_prefixes                  = [var.private_endpoint_subnet_prefix]
  private_endpoint_network_policies = "Enabled"

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [private_endpoint_network_policies]
  }
}
