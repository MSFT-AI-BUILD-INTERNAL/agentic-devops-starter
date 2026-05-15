variable "resource_group_name" {
  description = "Name of the resource group to create or reference"
  type        = string
  default     = "rg-agentic-devops"
}

variable "create_resource_group" {
  description = "Whether to create the resource group. If false, references an existing resource group with the same name."
  type        = bool
  default     = true
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "acr_name" {
  description = "Name of the Azure Container Registry. Must be globally unique and alphanumeric only."
  type        = string
  default     = "acragenticdevops"
}

variable "acr_sku" {
  description = "SKU tier for ACR (Basic, Standard, or Premium)"
  type        = string
  default     = "Standard"
}

variable "acr_admin_enabled" {
  description = "Enable admin user for ACR"
  type        = bool
  default     = false
}

# AKS variables - Commented out for App Service migration
# variable "aks_cluster_name" {
#   description = "Name of the Azure Kubernetes Service cluster"
#   type        = string
#   default     = "aks-agentic-devops"
# }
#
# variable "aks_dns_prefix" {
#   description = "DNS prefix for the AKS cluster"
#   type        = string
#   default     = "aks-agentic-devops"
# }
#
# variable "kubernetes_version" {
#   description = "Kubernetes version to use for the AKS cluster"
#   type        = string
#   default     = "1.32"
# }
#
# variable "node_count" {
#   description = "Initial number of nodes in the default node pool"
#   type        = number
#   default     = 2
# }
#
# variable "vm_size" {
#   description = "Size of the VMs in the default node pool"
#   type        = string
#   default     = "Standard_D2s_v3"
# }
#
# variable "enable_auto_scaling" {
#   description = "Enable auto-scaling for the default node pool"
#   type        = bool
#   default     = true
# }
#
# variable "min_node_count" {
#   description = "Minimum number of nodes when auto-scaling is enabled"
#   type        = number
#   default     = 1
# }
#
# variable "max_node_count" {
#   description = "Maximum number of nodes when auto-scaling is enabled"
#   type        = number
#   default     = 5
# }

# App Service variables
variable "app_service_plan_name" {
  description = "Name of the App Service Plan"
  type        = string
  default     = "asp-agentic-devops"
}

variable "app_service_plan_sku" {
  description = "SKU for the App Service Plan (P1v3, P2v3, P3v3)"
  type        = string
  default     = "P1v3"
}

variable "app_service_name" {
  description = "Name of the App Service (must be globally unique)"
  type        = string
  default     = "app-agentic-devops"
}

variable "backend_image_name" {
  description = "Name of the backend container image"
  type        = string
  default     = "agentic-devops-starter"
}

variable "azure_ai_project_endpoint" {
  description = "Azure AI Project endpoint URL"
  type        = string
  default     = ""
}

variable "azure_ai_model_deployment_name" {
  description = "Azure AI model deployment name"
  type        = string
  default     = ""
}

variable "azure_openai_api_version" {
  description = "Azure OpenAI API version"
  type        = string
  default     = "2024-02-15-preview"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "Development"
    Project     = "Agentic DevOps Starter"
    ManagedBy   = "Terraform"
  }
}

variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace for App Service monitoring"
  type        = string
  default     = "log-agentic-devops"
}

variable "log_analytics_sku" {
  description = "SKU tier for Log Analytics Workspace"
  type        = string
  default     = "PerGB2018"
}

variable "log_analytics_retention_days" {
  description = "Retention period in days for Log Analytics logs"
  type        = number
  default     = 30
}

# VNET variables - Commented out for App Service migration
# variable "vnet_name" {
#   description = "Name of the virtual network for AKS"
#   type        = string
#   default     = "vnet-agentic-devops"
# }
#
# variable "vnet_address_space" {
#   description = "Address space for the virtual network"
#   type        = string
#   default     = "10.1.0.0/16"
# }
#
# variable "aks_subnet_name" {
#   description = "Name of the AKS subnet"
#   type        = string
#   default     = "aks-subnet"
# }
#
# variable "aks_subnet_prefix" {
#   description = "Address prefix for AKS subnet"
#   type        = string
#   default     = "10.1.1.0/24"
# }

variable "ai_foundry_resource_id" {
  description = "Resource ID of the Azure AI Foundry (Cognitive Services) account for role assignment. Leave empty to skip."
  type        = string
  default     = ""
}

# Virtual Network variables (used for App Service VNet integration and private endpoints)
variable "vnet_name" {
  description = "Name of the virtual network"
  type        = string
  default     = "vnet-agentic-devops"
}

variable "vnet_address_space" {
  description = "Address space for the virtual network (CIDR)"
  type        = string
  default     = "10.10.0.0/16"
}

variable "app_integration_subnet_name" {
  description = "Name of the App Service VNet integration subnet"
  type        = string
  default     = "app-integration-subnet"
}

variable "app_integration_subnet_prefix" {
  description = "Address prefix for the App Service integration subnet"
  type        = string
  default     = "10.10.1.0/24"
}

variable "private_endpoint_subnet_name" {
  description = "Name of the private endpoint subnet"
  type        = string
  default     = "private-endpoint-subnet"
}

variable "private_endpoint_subnet_prefix" {
  description = "Address prefix for the private endpoint subnet"
  type        = string
  default     = "10.10.2.0/24"
}

# Blob Storage variables (for file uploads)
variable "storage_account_name" {
  description = "Name of the Azure Storage Account. Must be globally unique, 3-24 lowercase alphanumeric characters."
  type        = string
  default     = "stagenticdevops"
}

variable "uploads_container_name" {
  description = "Name of the blob container used for file uploads"
  type        = string
  default     = "uploads"
}

variable "storage_replication_type" {
  description = "Replication type for the storage account (LRS, ZRS, GRS, RAGRS)"
  type        = string
  default     = "LRS"
}

variable "storage_public_network_access_enabled" {
  description = "Allow storage account public network access. Defaults to false; access is via the private endpoint only."
  type        = bool
  default     = false
}

variable "storage_shared_access_key_enabled" {
  description = "Allow storage account shared key (account key) authentication. Defaults to false; access is via managed identity / Entra ID."
  type        = bool
  default     = false
}

