variable "vnet_name" {
  description = "Name of the virtual network"
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

variable "address_space" {
  description = "Address space for the virtual network (CIDR)"
  type        = string
  default     = "10.10.0.0/16"
}

variable "app_integration_subnet_name" {
  description = "Name of the subnet for App Service VNet integration"
  type        = string
  default     = "snet-app-integration"
}

variable "app_integration_subnet_prefix" {
  description = "Address prefix for the App Service integration subnet (CIDR)"
  type        = string
  default     = "10.10.1.0/24"
}

variable "private_endpoint_subnet_name" {
  description = "Name of the subnet for private endpoints"
  type        = string
  default     = "snet-private-endpoints"
}

variable "private_endpoint_subnet_prefix" {
  description = "Address prefix for the private endpoint subnet (CIDR)"
  type        = string
  default     = "10.10.2.0/24"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
