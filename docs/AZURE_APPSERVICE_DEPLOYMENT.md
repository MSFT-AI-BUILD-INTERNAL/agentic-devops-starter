# Azure App Service Deployment Guide

This guide covers the deployment of the Agentic DevOps application to Azure App Service using a **Sidecar Container** pattern, where Frontend (Nginx + React) and Backend (FastAPI) containers run in the same App Service instance sharing localhost.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Manual Deployment](#manual-deployment)
5. [CI/CD Deployment](#cicd-deployment)
6. [Updating the Application](#updating-the-application)
7. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
8. [Cleanup](#cleanup)

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │     Azure App Service (Sidecar Mode)     │
                    │     https://app-xxx.azurewebsites.net     │
   Browser ────────│─────────────────────────────────────────  │
                    │                                          │
                    │  ┌──────────────────────────────────┐    │
                    │  │  frontend (Nginx:80, isMain=true)   │    │
                    │  │    /         → React SPA            │    │
                    │  │    /api/*    → localhost:5100       │    │
                    │  └──────────────────────────────────┘    │
                    │          │ localhost shared (sidecar)     │
                    │  ┌──────────────────────────────────┐    │
                    │  │  backend (uvicorn:5100, sidecar)    │    │
                    │  │    FastAPI + AG-UI                  │    │
                    │  └──────────────────────────────────┘    │
                    └─────────────────────────────────────────┘
```

### Key Features

- **Sidecar Pattern**: Frontend and Backend containers share localhost network
- **Same-Origin**: Browser sees single domain → no CORS issues
- **Managed Identity**: Secure authentication to Azure resources
- **Auto-scaling**: Azure App Service built-in scaling capabilities
- **Monitoring**: Integrated with Azure Log Analytics

## Prerequisites

### Required Tools

- Azure CLI >= 2.50
- Terraform >= 1.5.0
- Git

### Azure Requirements

- Azure subscription with Contributor access
- Azure CLI logged in: `az login`

### Optional

- Azure AI Foundry project (for AI features)

## Infrastructure Setup

### Step 1: Configure Terraform Variables

```bash
cd infra-appservice
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# Required: ACR name must be globally unique
acr_name = "acragenticdevopsXXXX"  # Replace XXXX with unique value

# Optional: Azure AI configuration
azure_ai_project_endpoint      = ""  # Your Azure AI endpoint
azure_ai_model_deployment_name = "gpt-4o"

# Location and naming
location     = "eastus"
environment  = "dev"
project_name = "agenticdevops"

# App Service SKU (B1, B2, S1, S2, P1v3, etc.)
app_service_sku = "B1"
```

### Step 2: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan -out=tfplan

# Apply the configuration
terraform apply tfplan
```

This creates:
- Resource Group
- Azure Container Registry (ACR)
- App Service Plan (Linux)
- Web App with Sidecar containers
- Log Analytics Workspace
- Managed Identity and role assignments

### Step 3: Capture Outputs

```bash
# Save important values
export ACR_NAME=$(terraform output -raw acr_name)
export WEBAPP_NAME=$(terraform output -raw webapp_name)
export RESOURCE_GROUP=$(terraform output -raw resource_group_name)
export APP_URL=$(terraform output -raw app_url)

echo "ACR Name: $ACR_NAME"
echo "Web App: $WEBAPP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "App URL: $APP_URL"
```

## Manual Deployment

### Step 1: Build and Push Backend Image

```bash
# Navigate to project root
cd ..

# Build and push backend image to ACR
az acr build \
  --registry $ACR_NAME \
  --image agenticdevops-backend:latest \
  --image agenticdevops-backend:$(date +%Y%m%d-%H%M%S) \
  --file docker-appservice/Dockerfile.backend \
  .
```

### Step 2: Build and Push Frontend Image

```bash
# Build and push frontend image to ACR
az acr build \
  --registry $ACR_NAME \
  --image agenticdevops-frontend:latest \
  --image agenticdevops-frontend:$(date +%Y%m%d-%H%M%S) \
  --file docker-appservice/Dockerfile.frontend \
  .
```

### Step 3: Restart App Service

```bash
# Restart to pull latest images
az webapp restart \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP

# Wait for startup (about 1-2 minutes)
echo "Waiting for app to start..."
sleep 60
```

### Step 4: Verify Deployment

```bash
# Check health
curl https://${APP_URL#https://}/health

# Check API health
curl https://${APP_URL#https://}/api/health

# View logs
az webapp log tail \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP
```

## CI/CD Deployment

### Required GitHub Secrets

Set these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `AZURE_CLIENT_ID` | Service Principal Client ID | From Azure AD App Registration |
| `AZURE_TENANT_ID` | Azure Tenant ID | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `az account show --query id -o tsv` |
| `ACR_NAME` | Container Registry name | From Terraform output |
| `RESOURCE_GROUP` | Resource Group name | From Terraform output |
| `WEBAPP_NAME` | Web App name | From Terraform output |

### Setting up OIDC Authentication

1. Create Azure AD App Registration:
```bash
az ad app create --display-name "GitHub-Actions-AgenticDevOps"
```

2. Create Service Principal:
```bash
APP_ID=$(az ad app list --display-name "GitHub-Actions-AgenticDevOps" --query [0].appId -o tsv)
az ad sp create --id $APP_ID
```

3. Assign Contributor role:
```bash
SP_ID=$(az ad sp list --display-name "GitHub-Actions-AgenticDevOps" --query [0].id -o tsv)
az role assignment create \
  --role Contributor \
  --assignee $SP_ID \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID
```

4. Configure Federated Credentials:
```bash
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "GitHub-Actions",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:MSFT-AI-BUILD-INTERNAL/agentic-devops-starter:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Triggering Deployment

The workflow automatically runs on:
- Push to `main` branch
- Manual trigger via GitHub Actions UI

## Updating the Application

### Backend Only

```bash
az acr build --registry $ACR_NAME \
  --image agenticdevops-backend:latest \
  --file docker-appservice/Dockerfile.backend .

az webapp restart --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

### Frontend Only

```bash
az acr build --registry $ACR_NAME \
  --image agenticdevops-frontend:latest \
  --file docker-appservice/Dockerfile.frontend .

az webapp restart --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

### Both

```bash
az acr build --registry $ACR_NAME \
  --image agenticdevops-backend:latest \
  --file docker-appservice/Dockerfile.backend .

az acr build --registry $ACR_NAME \
  --image agenticdevops-frontend:latest \
  --file docker-appservice/Dockerfile.frontend .

az webapp restart --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

## Monitoring and Troubleshooting

### View Live Logs

```bash
az webapp log tail \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP
```

### Download Logs

```bash
az webapp log download \
  --name $WEBAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --log-file app-logs.zip
```

### Check Container Status

```bash
# View sidecar containers
az rest --method GET \
  --uri "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$WEBAPP_NAME/sitecontainers?api-version=2024-04-01" \
  --query "value[].{name:name, isMain:properties.isMain, image:properties.image, port:properties.targetPort}" \
  --output table
```

### Common Issues

#### 1. Images Not Pulling

**Symptom**: Containers fail to start
**Solution**: 
```bash
# Verify ACR access
az acr repository list --name $ACR_NAME --output table

# Check managed identity
az webapp identity show --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

#### 2. Backend Not Responding (502/503)

**Symptom**: `/api/*` requests fail
**Solution**: Backend container may still be starting (can take 1-2 minutes)
```bash
# Check logs for backend startup
az webapp log tail --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP | grep backend
```

#### 3. CORS Errors

**Symptom**: Browser shows CORS errors
**Solution**: This shouldn't happen with sidecar pattern. Verify:
```bash
# Check that nginx config is correct
az webapp config show --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

### Health Checks

```bash
# Frontend health
curl https://${APP_URL#https://}/health

# Backend health (via proxy)
curl https://${APP_URL#https://}/api/health

# Get detailed status
curl -v https://${APP_URL#https://}/api/health
```

## Cleanup

To remove all Azure resources:

```bash
cd infra-appservice
terraform destroy -auto-approve
```

This will delete:
- App Service and App Service Plan
- Container Registry (and all images)
- Log Analytics Workspace
- Resource Group

**Warning**: This is irreversible. All data and configurations will be lost.

## Additional Resources

- [Azure App Service Sidecar Containers](https://learn.microsoft.com/en-us/azure/app-service/tutorial-custom-container-sidecar)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Managed Identity](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
