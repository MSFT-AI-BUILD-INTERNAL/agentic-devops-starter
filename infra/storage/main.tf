# Azure Storage Account for file uploads, locked down to private endpoint access only.
#
# Public network access is disabled so blobs are only reachable via the private
# endpoint deployed into the caller-supplied subnet. A private DNS zone for
# `privatelink.blob.core.windows.net` is created and linked to the VNet so the
# App Service resolves the storage hostname to the private endpoint IP.
resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = var.replication_type
  account_kind             = "StorageV2"

  # Security hardening
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = var.shared_access_key_enabled
  public_network_access_enabled   = var.public_network_access_enabled

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  # Default to denying all public traffic; access is only via private endpoint.
  network_rules {
    default_action = var.public_network_access_enabled ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

# Blob container for user uploads.
resource "azurerm_storage_container" "uploads" {
  name                  = var.uploads_container_name
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"

  depends_on = [azurerm_storage_account.main]
}

# Private DNS zone for Blob private endpoint resolution.
resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob" {
  name                  = "${var.storage_account_name}-blob-dns-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blob.name
  virtual_network_id    = var.vnet_id

  tags = var.tags
}

# Private endpoint for the Blob sub-resource of the storage account.
resource "azurerm_private_endpoint" "blob" {
  name                = "${var.storage_account_name}-blob-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.storage_account_name}-blob-psc"
    private_connection_resource_id = azurerm_storage_account.main.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "blob-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }

  tags = var.tags

  depends_on = [
    azurerm_storage_account.main,
    azurerm_private_dns_zone_virtual_network_link.blob,
  ]
}

# Grant the App Service managed identity write access to the container so it
# can perform multi-part uploads without storage account keys.
resource "azurerm_role_assignment" "app_blob_contributor" {
  count                            = var.app_service_principal_id != "" ? 1 : 0
  scope                            = azurerm_storage_account.main.id
  role_definition_name             = "Storage Blob Data Contributor"
  principal_id                     = var.app_service_principal_id
  skip_service_principal_aad_check = true

  depends_on = [azurerm_storage_account.main]
}
