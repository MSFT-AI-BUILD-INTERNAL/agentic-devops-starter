# Azure App Configuration store with a sample feature flag.
#
# Standard SKU is required for feature flags and key-value soft-delete.
# Local (shared-key) auth is disabled so that callers must use Azure AD
# (DefaultAzureCredential) and the App Configuration Data Reader role.
resource "azurerm_app_configuration" "main" {
  name                       = var.app_configuration_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  sku                        = var.sku
  local_auth_enabled         = var.local_auth_enabled
  public_network_access      = var.public_network_access
  purge_protection_enabled   = var.purge_protection_enabled
  soft_delete_retention_days = var.soft_delete_retention_days

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Sample feature flag.
#
# Demonstrates centralised feature management. The backend
# `app/feature_flags.py` reads this flag using DefaultAzureCredential.
# Authoring this resource requires data-plane writer permissions on the
# store; the AzureRM provider auto-uses the AAD identity running
# `terraform apply`.
resource "azurerm_app_configuration_feature" "sample" {
  configuration_store_id = azurerm_app_configuration.main.id
  name                   = var.sample_feature_flag_name
  description            = var.sample_feature_flag_description
  enabled                = var.sample_feature_flag_enabled
}
