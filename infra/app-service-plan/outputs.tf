output "service_plan_id" {
  description = "ID of the App Service Plan"
  value       = azurerm_service_plan.main.id
}

output "service_plan_name" {
  description = "Name of the App Service Plan"
  value       = azurerm_service_plan.main.name
}
