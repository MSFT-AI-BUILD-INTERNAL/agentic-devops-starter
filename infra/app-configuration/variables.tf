variable "app_configuration_name" {
  description = "Name of the Azure App Configuration store. Must be globally unique, 5-50 chars, alphanumeric and hyphens."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-]{5,50}$", var.app_configuration_name))
    error_message = "App Configuration name must be 5-50 characters and contain only alphanumeric characters and hyphens."
  }
}

variable "resource_group_name" {
  description = "Name of the resource group where App Configuration will be created"
  type        = string
}

variable "location" {
  description = "Azure region where App Configuration will be deployed"
  type        = string
}

variable "sku" {
  description = "SKU tier for App Configuration (free or standard). Standard is required for feature flags."
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["free", "standard"], var.sku)
    error_message = "SKU must be one of: free, standard."
  }
}

variable "local_auth_enabled" {
  description = "Allow shared-key (connection string) auth. Disabled by default to enforce AAD-only access."
  type        = bool
  default     = false
}

variable "public_network_access" {
  description = "Public network access (Enabled or Disabled). Use Disabled with private endpoints for production."
  type        = string
  default     = "Enabled"

  validation {
    condition     = contains(["Enabled", "Disabled"], var.public_network_access)
    error_message = "public_network_access must be Enabled or Disabled."
  }
}

variable "purge_protection_enabled" {
  description = "Enable purge protection. Once enabled it cannot be disabled."
  type        = bool
  default     = false
}

variable "soft_delete_retention_days" {
  description = "Soft-delete retention in days (1-7). Standard SKU only."
  type        = number
  default     = 7
}

variable "sample_feature_flag_name" {
  description = "Name of the sample feature flag seeded in the store"
  type        = string
  default     = "Beta"
}

variable "sample_feature_flag_description" {
  description = "Description of the sample feature flag"
  type        = string
  default     = "Sample feature flag managed by Azure App Configuration."
}

variable "sample_feature_flag_enabled" {
  description = "Initial state of the sample feature flag"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to App Configuration resources"
  type        = map(string)
  default     = {}
}
