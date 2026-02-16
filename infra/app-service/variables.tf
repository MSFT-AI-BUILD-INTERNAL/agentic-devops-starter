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

variable "docker_registry_url" {
  description = "URL of the Docker registry (e.g., https://myacr.azurecr.io)"
  type        = string
}

variable "backend_image_tag" {
  description = "Docker image and tag for backend container (e.g., myacr.azurecr.io/backend:latest)"
  type        = string
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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
