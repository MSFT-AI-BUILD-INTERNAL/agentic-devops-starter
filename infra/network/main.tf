# Virtual Network for AKS
resource "azurerm_virtual_network" "main" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.vnet_address_space]
  tags                = var.tags
}

# Subnet for AKS nodes
# Note: default_outbound_access_enabled = false causes Azure to auto-create
# a subnet-level NSG named "{vnet}-{subnet}-nsg-{location}".
# We reference it via data source and add rules, avoiding import issues.
resource "azurerm_subnet" "aks" {
  name                            = var.aks_subnet_name
  resource_group_name             = var.resource_group_name
  virtual_network_name            = azurerm_virtual_network.main.name
  address_prefixes                = [var.aks_subnet_prefix]
  default_outbound_access_enabled = false
}

# Reference the auto-created subnet NSG (created by Azure when
# default_outbound_access_enabled = false)
data "azurerm_network_security_group" "aks" {
  name                = "${var.vnet_name}-${var.aks_subnet_name}-nsg-${var.location}"
  resource_group_name = var.resource_group_name

  depends_on = [azurerm_subnet.aks]
}

# Allow inbound HTTP and Istio-status from Internet for Load Balancer traffic
# Note: Add port 443 back when HTTPS/TLS is configured on the Istio Gateway
resource "azurerm_network_security_rule" "allow_http_inbound" {
  name                        = "AllowHTTPInbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["80", "15021"]
  source_address_prefix       = "Internet"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = data.azurerm_network_security_group.aks.name
}
