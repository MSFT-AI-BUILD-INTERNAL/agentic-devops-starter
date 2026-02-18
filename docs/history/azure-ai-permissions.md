# This file contains role assignments for the Managed Identity to access Azure AI resources
# You need to manually configure these based on your Azure AI Foundry project

# Example: Grant Azure AI Developer role to the managed identity
# This would be done in the Azure AI Foundry portal or via Azure CLI:
#
# az role assignment create \
#   --assignee <WORKLOAD_IDENTITY_PRINCIPAL_ID> \
#   --role "Azure AI Developer" \
#   --scope <AZURE_AI_PROJECT_RESOURCE_ID>
#
# Or Cognitive Services User role:
#
# az role assignment create \
#   --assignee <WORKLOAD_IDENTITY_PRINCIPAL_ID> \
#   --role "Cognitive Services User" \
#   --scope <AZURE_AI_PROJECT_RESOURCE_ID>

# Terraform alternative (add to main.tf if you have the Azure AI project resource ID):
# resource "azurerm_role_assignment" "ai_developer" {
#   principal_id         = module.managed_identity.identity_principal_id
#   role_definition_name = "Cognitive Services User"
#   scope                = var.azure_ai_project_resource_id
# }
