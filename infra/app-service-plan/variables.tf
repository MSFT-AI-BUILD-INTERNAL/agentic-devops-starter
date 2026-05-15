variable "service_plan_name" {
  description = "Name of the App Service Plan"
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

variable "sku_name" {
  description = "SKU name for the App Service Plan (e.g., P1v3, P2v3, P3v3)"
  type        = string
  default     = "P1v3"
}

variable "create" {
  description = "Whether Terraform should create the App Service Plan. Defaults to false: the plan is expected to exist. Set to true for greenfield deployments."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
