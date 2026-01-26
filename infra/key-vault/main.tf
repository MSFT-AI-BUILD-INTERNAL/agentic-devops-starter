# Data source to get current client configuration
data "azurerm_client_config" "current" {}

# Azure Key Vault for SSL Certificates
resource "azurerm_key_vault" "main" {
  name                       = var.key_vault_name
  location                   = var.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = var.key_vault_sku
  soft_delete_retention_days = var.soft_delete_retention_days
  purge_protection_enabled   = var.purge_protection_enabled

  # Enable for Application Gateway integration
  enabled_for_deployment          = true
  enabled_for_disk_encryption     = false
  enabled_for_template_deployment = true

  # Network rules for security
  network_acls {
    bypass         = "AzureServices"
    default_action = var.key_vault_network_default_action
  }

  tags = var.tags
}

# Access policy for the current user/service principal (for initial setup)
resource "azurerm_key_vault_access_policy" "current_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  certificate_permissions = [
    "Get",
    "List",
    "Create",
    "Import",
    "Update",
    "Delete",
    "Purge",
    "Recover",
  ]

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover",
  ]

  key_permissions = [
    "Get",
    "List",
    "Create",
    "Delete",
    "Purge",
    "Recover",
  ]
}

# Access policy for Application Gateway Managed Identity
resource "azurerm_key_vault_access_policy" "app_gateway" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = var.app_gateway_identity_principal_id

  certificate_permissions = [
    "Get",
    "List",
  ]

  secret_permissions = [
    "Get",
    "List",
  ]
}

# Self-signed certificate for testing (optional - can be replaced with real certificate)
resource "azurerm_key_vault_certificate" "app_gateway_cert" {
  count        = var.create_self_signed_cert ? 1 : 0
  name         = var.certificate_name
  key_vault_id = azurerm_key_vault.main.id

  certificate_policy {
    issuer_parameters {
      name = "Self"
    }

    key_properties {
      exportable = true
      key_size   = 2048
      key_type   = "RSA"
      reuse_key  = true
    }

    lifetime_action {
      action {
        action_type = "AutoRenew"
      }

      trigger {
        days_before_expiry = 30
      }
    }

    secret_properties {
      content_type = "application/x-pkcs12"
    }

    x509_certificate_properties {
      extended_key_usage = ["1.3.6.1.5.5.7.3.1"]

      key_usage = [
        "cRLSign",
        "dataEncipherment",
        "digitalSignature",
        "keyAgreement",
        "keyCertSign",
        "keyEncipherment",
      ]

      subject            = "CN=${var.certificate_subject}"
      validity_in_months = 12

      subject_alternative_names {
        dns_names = var.certificate_dns_names
      }
    }
  }

  depends_on = [
    azurerm_key_vault_access_policy.current_user
  ]
}
