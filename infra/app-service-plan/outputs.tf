output "service_plan_id" {
  description = "ID of the App Service Plan"
  value       = local.plan.id
}

output "service_plan_name" {
  description = "Name of the App Service Plan"
  value       = local.plan.name
}
