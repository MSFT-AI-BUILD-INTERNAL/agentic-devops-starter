variable "key_vault_name" {
  description = "Name of the Azure Key Vault (must be globally unique, 3-24 characters)"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-]{3,24}$", var.key_vault_name))
    error_message = "Key Vault name must be 3-24 characters and contain only alphanumeric characters and hyphens."
  }
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "key_vault_sku" {
  description = "SKU for Key Vault (standard or premium)"
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["standard", "premium"], var.key_vault_sku)
    error_message = "Key Vault SKU must be either 'standard' or 'premium'."
  }
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain deleted Key Vault (7-90 days)"
  type        = number
  default     = 7

  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "Soft delete retention days must be between 7 and 90."
  }
}

variable "purge_protection_enabled" {
  description = "Enable purge protection for Key Vault (prevents permanent deletion)"
  type        = bool
  default     = false
}

variable "key_vault_network_default_action" {
  description = "Default action for Key Vault network rules (Allow or Deny)"
  type        = string
  default     = "Allow"

  validation {
    condition     = contains(["Allow", "Deny"], var.key_vault_network_default_action)
    error_message = "Network default action must be either 'Allow' or 'Deny'."
  }
}

variable "app_gateway_identity_principal_id" {
  description = "Principal ID of the Application Gateway managed identity"
  type        = string
}

variable "create_self_signed_cert" {
  description = "Create a self-signed certificate for testing (true) or use imported certificate (false)"
  type        = bool
  default     = true
}

variable "certificate_name" {
  description = "Name of the certificate in Key Vault"
  type        = string
  default     = "app-gateway-ssl-cert"
}

variable "certificate_subject" {
  description = "Subject for the self-signed certificate"
  type        = string
  default     = "agentic-devops.local"
}

variable "certificate_dns_names" {
  description = "DNS names for the certificate (Subject Alternative Names)"
  type        = list(string)
  default     = ["agentic-devops.local", "*.agentic-devops.local"]
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
