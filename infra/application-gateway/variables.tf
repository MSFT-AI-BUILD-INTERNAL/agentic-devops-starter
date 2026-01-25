variable "appgw_name" {
  description = "Name of the Application Gateway"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for the Application Gateway"
  type        = string
}

variable "subnet_id" {
  description = "ID of the subnet where Application Gateway will be deployed"
  type        = string
}

variable "public_ip_name" {
  description = "Name of the public IP for Application Gateway"
  type        = string
}

variable "sku_name" {
  description = "SKU name for Application Gateway"
  type        = string
  default     = "Standard_v2"

  validation {
    condition     = contains(["Standard_Small", "Standard_Medium", "Standard_Large", "Standard_v2", "WAF_Medium", "WAF_Large", "WAF_v2"], var.sku_name)
    error_message = "SKU name must be a valid Application Gateway SKU."
  }
}

variable "sku_tier" {
  description = "SKU tier for Application Gateway"
  type        = string
  default     = "Standard_v2"

  validation {
    condition     = contains(["Standard", "Standard_v2", "WAF", "WAF_v2"], var.sku_tier)
    error_message = "SKU tier must be a valid Application Gateway SKU tier."
  }
}

variable "capacity" {
  description = "Number of instances for Application Gateway"
  type        = number
  default     = 2

  validation {
    condition     = var.capacity >= 1 && var.capacity <= 125
    error_message = "Capacity must be between 1 and 125."
  }
}

variable "backend_fqdns" {
  description = "List of backend FQDNs for the Application Gateway backend pool (e.g., AKS ingress IPs or LoadBalancer IPs)"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to Application Gateway resources"
  type        = map(string)
  default     = {}
}
