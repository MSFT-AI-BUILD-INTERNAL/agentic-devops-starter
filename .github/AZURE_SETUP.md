# Azure OIDC Setup for GitHub Actions

## Prerequisites
- Azure Subscription
- GitHub repository with admin access
- Azure CLI installed

## Setup Steps

### 1. Create Azure AD Application

```bash
# Set variables
REPO_OWNER="MSFT-AI-BUILD-INTERNAL"
REPO_NAME="agentic-devops-starter"
APP_NAME="gh-actions-agentic-devops"

# Create Azure AD app
az ad app create --display-name "$APP_NAME"

# Get the application ID
APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)
echo "Application ID: $APP_ID"

# Get the tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "Tenant ID: $TENANT_ID"

# Get the subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Subscription ID: $SUBSCRIPTION_ID"
```

### 2. Create Service Principal

```bash
# Create service principal
az ad sp create --id $APP_ID

# Get the object ID of the service principal
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query "id" -o tsv)
echo "Service Principal Object ID: $SP_OBJECT_ID"
```

### 3. Configure Federated Identity Credentials

```bash
# For main branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "gh-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$REPO_OWNER"'/'"$REPO_NAME"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# For all branches (optional)
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "gh-actions-all-branches",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$REPO_OWNER"'/'"$REPO_NAME"':ref:refs/heads/*",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# For pull requests (optional)
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "gh-actions-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$REPO_OWNER"'/'"$REPO_NAME"':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 4. Assign Azure Roles

```bash
# Assign Contributor role for the subscription
az role assignment create \
  --assignee $APP_ID \
  --role Contributor \
  --scope /subscriptions/$SUBSCRIPTION_ID

# If you have specific resource groups, use:
RESOURCE_GROUP="rg-agentic-devops"
az role assignment create \
  --assignee $APP_ID \
  --role Contributor \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP

# For ACR push/pull
ACR_NAME="your-acr-name"
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
az role assignment create \
  --assignee $APP_ID \
  --role AcrPush \
  --scope $ACR_ID
```

### 5. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

```
# ⚠️ CRITICAL: Use the correct Client ID!
# AZURE_CLIENT_ID must be the GitHub Actions App ID (from step 1)
# DO NOT use any other service principal or managed identity!
AZURE_CLIENT_ID: <APP_ID from step 1>
AZURE_TENANT_ID: <TENANT_ID from step 1>
AZURE_SUBSCRIPTION_ID: <SUBSCRIPTION_ID from step 1>

# Infrastructure configuration (from Terraform outputs)
ACR_NAME: <your-acr-name>
APP_SERVICE_NAME: <your-app-service-name>
RESOURCE_GROUP: <your-resource-group-name>

# Application configuration (optional)
AZURE_AI_PROJECT_ENDPOINT: <your-azure-ai-endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME: <your-model-deployment-name>
AZURE_OPENAI_API_VERSION: <api-version>
```

**Common Mistake to Avoid:**

❌ **WRONG**: Using the wrong identity
```bash
# These are NOT the correct values for AZURE_CLIENT_ID:
# Do not use App Service managed identity or any other identity
```

✅ **CORRECT**: Using GitHub Actions App ID
```bash
# This is the correct value for AZURE_CLIENT_ID:
az ad app list --display-name "gh-actions-agentic-devops" --query "[0].appId" -o tsv
```

### 6. Verify Setup

```bash
# List federated credentials
az ad app federated-credential list --id $APP_ID

# Verify role assignments
az role assignment list --assignee $APP_ID --output table
```

## Troubleshooting

### Error: "No subscription found"
- Verify `AZURE_SUBSCRIPTION_ID` is correct
- Check if service principal has access to the subscription

### Error: "AADSTS70021: No matching federated identity"
- Check the subject claim matches your repo and branch
- Verify the issuer is `https://token.actions.githubusercontent.com`
- Ensure audiences includes `api://AzureADTokenExchange`

### Error: "AuthorizationFailed"
- Verify role assignments are configured
- Check if service principal has required permissions

## Alternative: Using Client Secret (Less Secure)

If OIDC setup fails, you can use client secret:

```bash
# Create client secret
SECRET=$(az ad app credential reset --id $APP_ID --query password -o tsv)
echo "Client Secret: $SECRET"
```

Then add to GitHub secrets a single `AZURE_CREDENTIALS` secret with the following JSON object:

```json
{
  "clientId": "<APP_ID from step 1>",
  "clientSecret": "<SECRET from above>",
  "subscriptionId": "<SUBSCRIPTION_ID from step 1>",
  "tenantId": "<TENANT_ID from step 1>"
}
```

And update the workflow to use the `creds` parameter instead of individual IDs:

```yaml
- name: Azure Login
  uses: azure/login@v2
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}
```
