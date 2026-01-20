# Azure Credential Configuration Guide

This guide explains how to configure Azure credentials for the Agentic DevOps Starter application in different environments.

## Overview

The application uses Azure Identity for authentication to access Azure AI Foundry services. The authentication method varies depending on the deployment environment:

- **Local Development**: Uses `DefaultAzureCredential` (tries multiple methods)
- **AKS Deployment**: Uses `ManagedIdentityCredential` with a specific client ID

## Problem: Multiple Managed Identities

When deploying to AKS, you may encounter this error:

```
DefaultAzureCredential failed to retrieve a token from the included credentials.
...
ManagedIdentityCredential: Multiple user assigned identities exist, please specify the clientId / resourceId of the identity in the token request
```

This error occurs because:
1. AKS clusters have multiple managed identities (kubelet identity, control plane identity, etc.)
2. The application needs to know which specific identity to use
3. Without specifying a client ID, Azure doesn't know which identity to authenticate with

## Solution: Configure AZURE_CLIENT_ID

### For AKS/Kubernetes Deployment

The application now supports specifying which managed identity to use via the `AZURE_CLIENT_ID` environment variable.

#### Step 1: Identify the Managed Identity Client ID

The managed identity client ID you need depends on what identity has been granted access to your Azure AI Foundry resources.

**Option A: Use the AKS Kubelet Identity (Recommended)**

The kubelet identity is the identity used by AKS to pull container images and access Azure resources:

```bash
# Get the kubelet identity client ID
az aks show --resource-group <resource-group> --name <cluster-name> \
  --query identityProfile.kubeletidentity.clientId -o tsv
```

**Option B: Use a User-Assigned Managed Identity**

If you've created a specific user-assigned managed identity:

```bash
# List all user-assigned identities in the resource group
az identity list --resource-group <resource-group> --query "[].{name:name, clientId:clientId}" -o table

# Get a specific identity's client ID
az identity show --name <identity-name> --resource-group <resource-group> --query clientId -o tsv
```

#### Step 2: Grant the Identity Access to Azure AI Foundry

The managed identity needs the "Cognitive Services OpenAI User" role on your Azure AI Foundry resource:

```bash
# Get the identity's principal ID (object ID)
PRINCIPAL_ID=$(az aks show --resource-group <resource-group> --name <cluster-name> \
  --query identityProfile.kubeletidentity.objectId -o tsv)

# Grant access to Azure AI Foundry
az role assignment create \
  --role "Cognitive Services OpenAI User" \
  --assignee-object-id $PRINCIPAL_ID \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<azure-ai-resource>
```

#### Step 3: Configure GitHub Secrets

Add the following secret to your GitHub repository (Settings → Secrets and variables → Actions):

- **`AZURE_MANAGED_IDENTITY_CLIENT_ID`**: The client ID from Step 1

Also ensure you have:
- **`AZURE_TENANT_ID`**: Your Azure tenant ID
- **`AZURE_AI_PROJECT_ENDPOINT`**: Your Azure AI Foundry endpoint (e.g., `https://your-resource.openai.azure.com/`)
- **`AZURE_AI_MODEL_DEPLOYMENT_NAME`**: Your model deployment name (e.g., `gpt-4o-mini`)
- **`AZURE_OPENAI_API_VERSION`**: API version (e.g., `2025-08-07`)

The GitHub Actions workflow will automatically create the Kubernetes secret with these values.

#### Step 4: Verify Configuration

After deployment, check the pod logs:

```bash
# Get pod logs
kubectl logs -l app=agentic-devops -c backend

# You should see:
# INFO:__main__:Using ManagedIdentityCredential with client_id: <your-client-id>
```

### For Local Development

For local development, you have several options:

#### Option 1: Use Azure CLI Authentication (Recommended)

```bash
# Login to Azure
az login

# Set the subscription
az account set --subscription <subscription-id>

# No environment variables needed - DefaultAzureCredential will use Azure CLI
```

#### Option 2: Use Environment Variables

Create a `.env` file in the `app` directory:

```bash
# Azure AI Configuration
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-08-07

# Option A: Use Azure CLI (no additional variables needed)
# Just run: az login

# Option B: Use Service Principal
AZURE_CLIENT_ID=<service-principal-client-id>
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_SECRET=<service-principal-secret>

# Option C: Use API Key (not recommended for production)
AZURE_OPENAI_API_KEY=<your-api-key>
```

#### Option 3: Use Managed Identity (if running on Azure VM)

If running on an Azure VM with a managed identity:

```bash
# Azure AI Configuration
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-08-07

# Specify which managed identity to use
AZURE_CLIENT_ID=<managed-identity-client-id>
```

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry endpoint | Yes | `https://your-resource.openai.azure.com/` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment name | Yes | `gpt-4o-mini` |
| `AZURE_OPENAI_API_VERSION` | API version | No (default: `2025-08-07`) | `2025-08-07` |
| `AZURE_CLIENT_ID` | Managed identity client ID | AKS: Yes, Local: No | `12345678-1234-1234-1234-123456789abc` |
| `AZURE_TENANT_ID` | Azure tenant ID | Optional | `87654321-4321-4321-4321-cba987654321` |
| `AZURE_OPENAI_API_KEY` | API key (alternative to managed identity) | No | `abc123...` |

## Troubleshooting

### Error: "Multiple user assigned identities exist"

**Problem**: The application can't determine which managed identity to use.

**Solution**: Set the `AZURE_CLIENT_ID` environment variable to specify the identity. See the AKS deployment section above.

### Error: "EnvironmentCredential authentication unavailable"

**Problem**: Required environment variables for EnvironmentCredential are not set.

**Solution**: This is expected when using managed identity. Ignore this message if you see "Using ManagedIdentityCredential" in the logs.

### Error: "Azure CLI not found on path"

**Problem**: Azure CLI is not installed or not in PATH.

**Solution**: 
- Install Azure CLI: https://docs.microsoft.com/cli/azure/install-azure-cli
- Or use a different authentication method (managed identity or service principal)

### Error: "ClientAuthenticationError: authentication failed"

**Problem**: The managed identity doesn't have permission to access Azure AI Foundry.

**Solution**: Grant the "Cognitive Services OpenAI User" role to the managed identity (see Step 2 in AKS deployment).

### Checking Current Authentication

To verify which authentication method is being used, check the application logs:

```bash
# For AKS
kubectl logs -l app=agentic-devops -c backend | grep -i credential

# For local development
# Check the console output when starting the server
```

You should see one of:
- `Using ManagedIdentityCredential with client_id: <id>` - Using specific managed identity
- `Using DefaultAzureCredential` - Trying multiple authentication methods

## Security Best Practices

1. **Never commit credentials**: Don't commit `.env` files or secrets to git
2. **Use managed identities**: Preferred for Azure deployments (no secrets to manage)
3. **Rotate secrets regularly**: If using API keys or service principals
4. **Least privilege**: Grant only the minimum required permissions
5. **Use Key Vault**: For storing sensitive configuration in production

## Additional Resources

- [Azure Identity Documentation](https://learn.microsoft.com/azure/developer/python/sdk/authentication-overview)
- [DefaultAzureCredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
- [ManagedIdentityCredential](https://learn.microsoft.com/python/api/azure-identity/azure.identity.managedidentitycredential)
- [Azure AI Foundry Authentication](https://learn.microsoft.com/azure/ai-services/openai/how-to/managed-identity)
