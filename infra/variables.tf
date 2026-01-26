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

# Application Gateway Configuration
variable "app_gateway_name" {
  description = "Name of the Application Gateway"
  type        = string
  default     = "appgw-agentic-devops"
}

variable "app_gateway_public_ip_name" {
  description = "Name of the public IP for Application Gateway"
  type        = string
  default     = "pip-appgw-agentic-devops"
}

variable "vnet_name" {
  description = "Name of the virtual network for Application Gateway and AKS"
  type        = string
  default     = "vnet-agentic-devops"
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = string
  default     = "10.1.0.0/16"
}

variable "appgw_subnet_name" {
  description = "Name of the Application Gateway subnet"
  type        = string
  default     = "appgw-subnet"
}

variable "appgw_subnet_prefix" {
  description = "Address prefix for Application Gateway subnet"
  type        = string
  default     = "10.1.0.0/24"
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

variable "app_gateway_sku_name" {
  description = "SKU name for Application Gateway (Standard_v2 or WAF_v2)"
  type        = string
  default     = "Standard_v2"
}

variable "app_gateway_sku_tier" {
  description = "SKU tier for Application Gateway (Standard_v2 or WAF_v2)"
  type        = string
  default     = "Standard_v2"
}

variable "app_gateway_capacity" {
  description = "Capacity (instance count) for Application Gateway"
  type        = number
  default     = 2
}

variable "waf_firewall_mode" {
  description = "Web Application Firewall mode (Detection or Prevention)"
  type        = string
  default     = "Detection"
}

# Key Vault Configuration for SSL Certificates
variable "enable_https" {
  description = "Enable HTTPS with SSL certificate from Key Vault"
  type        = bool
  default     = true
}

variable "key_vault_name" {
  description = "Name of the Azure Key Vault for SSL certificates (must be globally unique, 3-24 characters)"
  type        = string
  default     = "kv-agentic-devops"
}

variable "key_vault_sku" {
  description = "SKU for Key Vault (standard or premium)"
  type        = string
  default     = "standard"
}

variable "key_vault_soft_delete_retention_days" {
  description = "Number of days to retain deleted Key Vault (7-90 days)"
  type        = number
  default     = 7
}

variable "key_vault_purge_protection_enabled" {
  description = "Enable purge protection for Key Vault (prevents permanent deletion)"
  type        = bool
  default     = false
}

variable "key_vault_network_default_action" {
  description = "Default action for Key Vault network rules (Allow or Deny)"
  type        = string
  default     = "Allow"
}

variable "create_self_signed_cert" {
  description = "Create a self-signed certificate for testing (true) or use imported certificate (false)"
  type        = bool
  default     = true
}

variable "certificate_name" {
  description = "Name of the certificate in Key Vault"
  type        = string
  default     = "app-gateway-ssl-cert"
}

variable "ssl_certificate_name" {
  description = "Name for the SSL certificate in Application Gateway"
  type        = string
  default     = "appgw-ssl-certificate"
}

variable "certificate_subject" {
  description = "Subject for the self-signed certificate"
  type        = string
  default     = "agentic-devops.local"
}

variable "certificate_dns_names" {
  description = "DNS names for the certificate (Subject Alternative Names)"
  type        = list(string)
  default     = ["agentic-devops.local", "*.agentic-devops.local"]
}

