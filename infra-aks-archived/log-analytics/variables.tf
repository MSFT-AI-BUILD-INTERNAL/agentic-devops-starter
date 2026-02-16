variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group where Log Analytics Workspace will be created"
  type        = string
}

variable "location" {
  description = "Azure region where Log Analytics Workspace will be deployed"
  type        = string
}

variable "sku" {
  description = "SKU of the Log Analytics Workspace"
  type        = string
  default     = "PerGB2018"

  validation {
    condition     = contains(["Free", "PerNode", "Premium", "Standard", "Standalone", "Unlimited", "CapacityReservation", "PerGB2018"], var.sku)
    error_message = "SKU must be one of: Free, PerNode, Premium, Standard, Standalone, Unlimited, CapacityReservation, PerGB2018."
  }
}

variable "retention_in_days" {
  description = "The workspace data retention in days. Possible values are 30-730 days for paid tiers (PerGB2018, Standard, Premium, etc.). The Free tier is fixed at 7 days and cannot be configured."
  type        = number
  default     = 30

  validation {
    condition     = var.retention_in_days >= 7 && var.retention_in_days <= 730
    error_message = "Retention in days must be between 7 and 730. Note: Free tier only supports 7 days."
  }
}

variable "tags" {
  description = "Tags to apply to the Log Analytics Workspace"
  type        = map(string)
  default     = {}
}
