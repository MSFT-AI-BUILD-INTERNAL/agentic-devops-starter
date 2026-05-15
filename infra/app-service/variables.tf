variable "app_service_name" {
  description = "Name of the App Service"
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

variable "service_plan_id" {
  description = "ID of the App Service Plan"
  type        = string
}

variable "sku_name" {
  description = "SKU name of the App Service Plan (used to determine feature availability like always_on)"
  type        = string
  default     = "B1"
}

variable "docker_registry_url" {
  description = "URL of the Docker registry (e.g., https://myacr.azurecr.io)"
  type        = string
}

variable "docker_image_name" {
  description = "Docker image name (without registry prefix, e.g., agentic-devops-starter)"
  type        = string
}

variable "docker_image_tag" {
  description = "Docker image tag (e.g., latest, v1.0.0)"
  type        = string
  default     = "latest"
}

variable "acr_id" {
  description = "ID of the Azure Container Registry"
  type        = string
}

variable "ai_foundry_resource_id" {
  description = "Resource ID of the Azure AI Foundry project (optional)"
  type        = string
  default     = ""
}

variable "app_settings" {
  description = "Additional app settings (environment variables)"
  type        = map(string)
  default     = {}
}

variable "vnet_integration_subnet_id" {
  description = "ID of the subnet for regional VNet integration. Required for the App Service to reach private endpoints. Only used when enable_vnet_integration = true."
  type        = string
  default     = ""
}

variable "enable_vnet_integration" {
  description = "Whether to create the App Service regional VNet integration. Must be a plan-time-known boolean (not derived from another resource's attributes) so Terraform can resolve count statically."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
