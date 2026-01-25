output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

output "certificate_secret_id" {
  description = "Secret ID of the certificate (for Application Gateway)"
  value       = var.create_self_signed_cert && length(azurerm_key_vault_certificate.app_gateway_cert) > 0 ? azurerm_key_vault_certificate.app_gateway_cert[0].secret_id : "https://${azurerm_key_vault.main.vault_uri}secrets/${var.certificate_name}"
}

output "certificate_name" {
  description = "Name of the certificate in Key Vault"
  value       = var.certificate_name
}

output "key_vault_certificate_url" {
  description = "URL to the certificate in Key Vault (for manual import)"
  value       = "https://${azurerm_key_vault.main.vault_uri}certificates/${var.certificate_name}"
}
