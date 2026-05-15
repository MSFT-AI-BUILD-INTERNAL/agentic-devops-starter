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

resource "azurerm_storage_container" "containers" {
  for_each              = toset(var.container_names)
  name                  = each.value
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = var.container_access_type
}
