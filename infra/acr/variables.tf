variable "acr_name" {
  description = "Name of the Azure Container Registry. Must be globally unique and contain only alphanumeric characters."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9]{5,50}$", var.acr_name))
    error_message = "ACR name must be between 5 and 50 characters and contain only alphanumeric characters."
  }
}

variable "resource_group_name" {
  description = "Name of the resource group where ACR will be created"
  type        = string
}

variable "location" {
  description = "Azure region where ACR will be deployed"
  type        = string
}

variable "sku" {
  description = "SKU tier for ACR (Basic, Standard, or Premium)"
  type        = string
  default     = "Standard"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.sku)
    error_message = "SKU must be one of: Basic, Standard, Premium."
  }
}

variable "admin_enabled" {
  description = "Enable admin user for ACR"
  type        = bool
  default     = false
}

variable "public_network_access_enabled" {
  description = "Enable public network access to ACR. Set to false for production environments and use private endpoints instead."
  type        = bool
  default     = true # Set to true for easier initial setup; consider false for production
}

variable "identity_type" {
  description = "Type of managed identity (SystemAssigned, UserAssigned, or null for none)"
  type        = string
  default     = "SystemAssigned"

  validation {
    condition     = var.identity_type == null || contains(["SystemAssigned", "UserAssigned"], var.identity_type)
    error_message = "Identity type must be SystemAssigned, UserAssigned, or null."
  }
}

variable "tags" {
  description = "Tags to apply to the ACR resource"
  type        = map(string)
  default     = {}
}
