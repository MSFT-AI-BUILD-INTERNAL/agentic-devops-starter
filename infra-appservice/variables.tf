# ============================================================================
# variables.tf - Input variable definitions
# Azure App Service Sidecar configuration (Frontend=Main + Backend=Sidecar)
# ============================================================================

# ============================================================================
# Environment & Naming
# ============================================================================
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "agenticdevops"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens, 2-21 chars."
  }
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "agentic-devops"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

# ============================================================================
# App Service Configuration
# ============================================================================
variable "app_service_sku" {
  description = "App Service Plan SKU (B1, B2, S1, S2, P1v3, etc.)"
  type        = string
  default     = "B1"
}

variable "backend_docker_image" {
  description = "Backend Docker image name (FastAPI)"
  type        = string
  default     = "agenticdevops-backend"
}

variable "frontend_docker_image" {
  description = "Frontend Docker image name (Nginx + React SPA)"
  type        = string
  default     = "agenticdevops-frontend"
}

variable "always_on" {
  description = "Keep the app always running (requires Basic tier or higher)"
  type        = bool
  default     = true
}

variable "custom_domain" {
  description = "Custom domain for the app (e.g., app.example.com). Leave empty to use default azurewebsites.net domain."
  type        = string
  default     = ""
}

# ============================================================================
# ACR Configuration
# ============================================================================
variable "acr_name" {
  description = "Azure Container Registry name (must be globally unique, alphanumeric only)"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9]{5,50}$", var.acr_name))
    error_message = "ACR name must be 5-50 alphanumeric characters."
  }
}

variable "acr_sku" {
  description = "ACR SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Standard"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "ACR SKU must be one of: Basic, Standard, Premium."
  }
}

# ============================================================================
# Application Settings
# ============================================================================
variable "azure_ai_project_endpoint" {
  description = "Azure AI Foundry project endpoint URL (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_ai_model_deployment_name" {
  description = "Azure AI model deployment name (optional)"
  type        = string
  default     = "gpt-4o"
}

# ============================================================================
# Monitoring
# ============================================================================
variable "log_retention_days" {
  description = "Log Analytics workspace retention in days"
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "Log retention must be between 30 and 730 days."
  }
}
