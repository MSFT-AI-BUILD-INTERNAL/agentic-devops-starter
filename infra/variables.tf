variable "resource_group_name" {
  description = "Name of the resource group to create"
  type        = string
  default     = "rg-agentic-devops"
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

variable "aks_cluster_name" {
  description = "Name of the Azure Kubernetes Service cluster"
  type        = string
  default     = "aks-agentic-devops"
}

variable "aks_dns_prefix" {
  description = "DNS prefix for the AKS cluster"
  type        = string
  default     = "aks-agentic-devops"
}

variable "kubernetes_version" {
  description = "Kubernetes version to use for the AKS cluster"
  type        = string
  default     = "1.32"
}

variable "node_count" {
  description = "Initial number of nodes in the default node pool"
  type        = number
  default     = 2
}

variable "vm_size" {
  description = "Size of the VMs in the default node pool"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for the default node pool"
  type        = bool
  default     = true
}

variable "min_node_count" {
  description = "Minimum number of nodes when auto-scaling is enabled"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes when auto-scaling is enabled"
  type        = number
  default     = 5
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
  description = "Name of the Log Analytics Workspace for AKS monitoring"
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

variable "vnet_name" {
  description = "Name of the virtual network for AKS"
  type        = string
  default     = "vnet-agentic-devops"
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = string
  default     = "10.1.0.0/16"
}

variable "aks_subnet_name" {
  description = "Name of the AKS subnet"
  type        = string
  default     = "aks-subnet"
}

variable "aks_subnet_prefix" {
  description = "Address prefix for AKS subnet"
  type        = string
  default     = "10.1.1.0/24"
}

variable "ai_foundry_resource_id" {
  description = "Resource ID of the Azure AI Foundry (Cognitive Services) account for role assignment. Leave empty to skip."
  type        = string
  default     = ""
}

