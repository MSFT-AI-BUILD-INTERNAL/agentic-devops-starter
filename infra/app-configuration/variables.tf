variable "app_configuration_name" {
  description = "Name of the Azure App Configuration store. Must be globally unique."
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "sku" {
  description = "SKU for the App Configuration store (free or standard)."
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["free", "standard"], var.sku)
    error_message = "SKU must be one of: free, standard."
  }
}

variable "local_auth_enabled" {
  description = "Enable local authentication (access keys). Set to false to enforce Entra ID (RBAC) only."
  type        = bool
  default     = false
}

variable "public_network_access" {
  description = "Public network access mode: \"Enabled\", \"Disabled\", or null to leave unmanaged. Network exposure is governed by the separately-managed Private Endpoint stack."
  type        = string
  default     = null

  validation {
    condition     = var.public_network_access == null || contains(["Enabled", "Disabled"], coalesce(var.public_network_access, "unset"))
    error_message = "public_network_access must be \"Enabled\", \"Disabled\", or null."
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
