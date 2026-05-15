variable "storage_account_name" {
  description = "Name of the Azure Storage Account. Must be globally unique, 3-24 lowercase alphanumeric characters."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Storage account name must be 3-24 lowercase alphanumeric characters."
  }
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "uploads_container_name" {
  description = "Name of the blob container used for file uploads"
  type        = string
  default     = "uploads"
}

variable "replication_type" {
  description = "Replication type (LRS, ZRS, GRS, RAGRS, etc.)"
  type        = string
  default     = "LRS"
}

variable "vnet_id" {
  description = "ID of the virtual network to link the private DNS zone to"
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "ID of the subnet where the storage private endpoint will be created"
  type        = string
}

variable "app_service_principal_id" {
  description = "Principal ID of the App Service managed identity that needs Storage Blob Data Contributor access. Leave empty to skip the role assignment."
  type        = string
  default     = ""
}

variable "public_network_access_enabled" {
  description = "When true, the storage account is reachable over the public internet (in addition to the private endpoint). Recommended to keep false in production."
  type        = bool
  default     = false
}

variable "shared_access_key_enabled" {
  description = "When true, shared key (account key) auth is allowed. Recommended to keep false and rely on managed identity / Entra ID."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to storage resources"
  type        = map(string)
  default     = {}
}
