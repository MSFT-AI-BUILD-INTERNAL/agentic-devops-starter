variable "vnet_name" {
  description = "Name of the virtual network"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = string
}

variable "aks_subnet_name" {
  description = "Name of the AKS subnet"
  type        = string
}

variable "aks_subnet_prefix" {
  description = "Address prefix for AKS subnet"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
