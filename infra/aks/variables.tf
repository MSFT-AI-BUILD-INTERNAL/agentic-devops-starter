variable "aks_cluster_name" {
  description = "Name of the Azure Kubernetes Service cluster"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group where AKS will be created"
  type        = string
}

variable "location" {
  description = "Azure region where AKS will be deployed"
  type        = string
}

variable "dns_prefix" {
  description = "DNS prefix for the AKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version to use for the AKS cluster"
  type        = string
  default     = "1.28"
}

variable "default_node_pool_name" {
  description = "Name of the default node pool"
  type        = string
  default     = "default"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{0,11}$", var.default_node_pool_name))
    error_message = "Node pool name must start with a lowercase letter and contain only lowercase alphanumeric characters, max 12 characters."
  }
}

variable "node_count" {
  description = "Initial number of nodes in the default node pool"
  type        = number
  default     = 2

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 100
    error_message = "Node count must be between 1 and 100."
  }
}

variable "vm_size" {
  description = "Size of the VMs in the default node pool"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "os_disk_size_gb" {
  description = "OS disk size in GB for the nodes"
  type        = number
  default     = 30
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

variable "vnet_subnet_id" {
  description = "Subnet ID for the AKS cluster nodes (deprecated - use aks_subnet_id)"
  type        = string
  default     = null
}

variable "aks_subnet_id" {
  description = "Subnet ID for the AKS cluster nodes"
  type        = string
  default     = null
}

variable "app_gateway_id" {
  description = "ID of the Application Gateway for AGIC integration"
  type        = string
  default     = null
}

variable "network_plugin" {
  description = "Network plugin to use (azure or kubenet)"
  type        = string
  default     = "azure"

  validation {
    condition     = contains(["azure", "kubenet"], var.network_plugin)
    error_message = "Network plugin must be either 'azure' or 'kubenet'."
  }
}

variable "network_policy" {
  description = "Network policy to use (azure or calico)"
  type        = string
  default     = "azure"

  validation {
    condition     = contains(["azure", "calico"], var.network_policy)
    error_message = "Network policy must be either 'azure' or 'calico'."
  }
}

variable "load_balancer_sku" {
  description = "SKU of the load balancer (standard or basic)"
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["standard", "basic"], var.load_balancer_sku)
    error_message = "Load balancer SKU must be either 'standard' or 'basic'."
  }
}

variable "service_cidr" {
  description = "CIDR block for Kubernetes services"
  type        = string
  default     = "10.0.0.0/16"
}

variable "dns_service_ip" {
  description = "IP address for the Kubernetes DNS service"
  type        = string
  default     = "10.0.0.10"
}

variable "acr_id" {
  description = "ID of the Azure Container Registry to integrate with AKS"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to the AKS resource"
  type        = map(string)
  default     = {}
}

variable "log_analytics_workspace_id" {
  description = "ID of the Log Analytics Workspace for monitoring and logging"
  type        = string
  default     = null
}

variable "resource_group_id" {
  description = "ID of the resource group (for AGIC role assignment)"
  type        = string
  default     = null
}
