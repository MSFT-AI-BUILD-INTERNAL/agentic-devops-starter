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

variable "tags" {
  description = "Tags to apply to network resources"
  type        = map(string)
  default     = {}
}
