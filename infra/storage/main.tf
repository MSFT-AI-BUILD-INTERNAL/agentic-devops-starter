resource "azurerm_storage_account" "main" {
  name                          = var.storage_account_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  account_tier                  = var.account_tier
  account_replication_type      = var.replication_type
  public_network_access_enabled = var.public_network_access_enabled
  shared_access_key_enabled     = var.shared_access_key_enabled

  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"

  network_rules {
    default_action = "Deny"
    ip_rules       = var.allowed_ip_rules
    bypass         = ["AzureServices"]
  }

  blob_properties {
    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      account_tier,
      account_replication_type,
      account_kind,
      allow_nested_items_to_be_public,
      min_tls_version,
      blob_properties,
    ]
  }
}

# NOTE: Blob containers are NOT managed here because the azurerm provider uses
# data-plane APIs which cannot reach the storage account when
# public_network_access_enabled = false. Containers are created by deploy.sh
# via `az resource create` against the ARM container resource.
