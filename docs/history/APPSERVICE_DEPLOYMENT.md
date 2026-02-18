# Azure App Service Deployment Guide

This guide covers deploying the Agentic DevOps Starter to **Azure App Service** using a combined frontend + backend container with the sidecar pattern.

## Architecture Overview

The application uses a **single container** that runs both the frontend (React + nginx) and backend (FastAPI + Python) using supervisor:

```
┌─────────────────────────────────────────────────────────┐
│               Azure App Service                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Container (Dockerfile.appservice)               │  │
│  │  ┌────────────┐         ┌──────────────┐        │  │
│  │  │   nginx    │ ------> │   Backend    │        │  │
│  │  │  (port 80) │  proxy  │  (port 5100) │        │  │
│  │  │  Frontend  │  /api/* │   FastAPI    │        │  │
│  │  └────────────┘         └──────────────┘        │  │
│  │         │                                        │  │
│  │     Supervisor manages both processes           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  System-Assigned Managed Identity                       │
│  - AcrPull role on ACR                                  │
│  - Azure AI Developer on AI Foundry                     │
│  - Cognitive Services User                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────┐
        │  Azure Container Registry (ACR)     │
        │  - Store container image            │
        └────────────────────────────────────┘
```

## Prerequisites

### 1. Azure Resources

Before deploying, provision the infrastructure using Terraform:

```bash
cd infra

# Copy and configure variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values:
# - resource_group_name
# - location
# - acr_name (must be globally unique)
# - app_service_plan_name
# - app_service_name (must be globally unique)
# - ai_foundry_resource_id (optional)

# Initialize and apply
terraform init
terraform apply
```

This creates:
- **Resource Group**: Container for all resources
- **Azure Container Registry (ACR)**: Stores Docker images
- **Log Analytics Workspace**: Monitoring and logging
- **App Service Plan (P1v3)**: Linux plan with Docker support
- **App Service**: Web app with system-assigned managed identity

### 2. GitHub Actions Setup

#### Create Service Principal for OIDC

```bash
# Set variables
SUBSCRIPTION_ID="<your-subscription-id>"
RESOURCE_GROUP="<your-resource-group-name>"
APP_NAME="gh-actions-agentic-devops"

# Create service principal
az ad sp create-for-rbac \
  --name $APP_NAME \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP

# Note the output - you'll need:
# - appId (use for AZURE_CLIENT_ID)
# - tenant (use for AZURE_TENANT_ID)
```

#### Configure Federated Identity Credentials

```bash
# Get the Application (client) ID
APP_ID=$(az ad app list --display-name $APP_NAME --query "[0].appId" -o tsv)

# Create federated credential for main branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<YOUR_GITHUB_ORG>/<YOUR_REPO>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

#### Grant Additional Permissions

```bash
# Grant AcrPush role for pushing images
ACR_ID=$(az acr show --name <your-acr-name> --query id -o tsv)
SP_ID=$(az ad sp list --display-name $APP_NAME --query "[0].id" -o tsv)

az role assignment create \
  --assignee $SP_ID \
  --role AcrPush \
  --scope $ACR_ID
```

### 3. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

#### Required Secrets

```yaml
# Azure Authentication (OIDC)
AZURE_CLIENT_ID: <app-id-from-service-principal>
AZURE_TENANT_ID: <tenant-id>
AZURE_SUBSCRIPTION_ID: <subscription-id>

# Azure Resources (from Terraform outputs)
ACR_NAME: <acr-name>
APP_SERVICE_NAME: <app-service-name>
RESOURCE_GROUP: <resource-group-name>
```

#### Optional Application Secrets

```yaml
# Azure AI Configuration (if using Azure AI Foundry)
AZURE_AI_PROJECT_ENDPOINT: <your-azure-ai-endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME: <your-model-deployment>
AZURE_OPENAI_API_VERSION: 2024-02-15-preview
```

## Deployment Workflow

### Automatic Deployment

Push to the `main` branch triggers automatic deployment:

```bash
git push origin main
```

The workflow:
1. **Build**: Creates combined container image with frontend + backend
2. **Push**: Uploads to ACR with git SHA and `latest` tags
3. **Deploy**: Updates App Service with new image
4. **Verify**: Checks health endpoint

### Manual Deployment

Trigger manually from GitHub Actions:
1. Go to **Actions** tab
2. Select **Deploy to Azure App Service** workflow
3. Click **Run workflow**
4. Select branch and run

## Container Image Structure

The `Dockerfile.appservice` creates a multi-stage build:

### Stage 1: Build Frontend
- Uses Node.js 20 Alpine
- Installs npm dependencies
- Builds React app with Vite
- Output: `/dist` directory with static files

### Stage 2: Setup Backend
- Uses Python 3.12 slim
- Installs system dependencies (nginx, supervisor)
- Installs Python dependencies with `uv`
- Copies application code

### Stage 3: Combine
- Copies built frontend to `/usr/share/nginx/html`
- Configures nginx to:
  - Serve static files on port 8080
  - Proxy `/api/*` to backend on port 5100
  - Handle SPA routing
- Configures supervisor to run both nginx and backend
- Exposes port 8080 (App Service ingress)

## Configuration

### Environment Variables

App Service automatically injects these via `app_settings`:

```bash
WEBSITES_PORT=8080                     # Port for ingress
AZURE_TENANT_ID=<tenant-id>            # For managed identity
AZURE_AI_PROJECT_ENDPOINT=<endpoint>   # AI service
AZURE_AI_MODEL_DEPLOYMENT_NAME=<name>  # Model name
AZURE_OPENAI_API_VERSION=<version>     # API version
CORS_ORIGINS=*                         # Allow all origins
```

### Managed Identity

The App Service has a **system-assigned managed identity** with:
- **AcrPull**: Pull container images from ACR
- **Azure AI Developer**: Access Azure AI Foundry
- **Cognitive Services User**: Call AI APIs

Authentication happens automatically using `DefaultAzureCredential` in the backend.

## Monitoring and Logs

### View Logs

```bash
# Stream live logs
az webapp log tail \
  --resource-group <resource-group> \
  --name <app-service-name>

# Download logs
az webapp log download \
  --resource-group <resource-group> \
  --name <app-service-name>
```

### Log Analytics

App Service sends logs to Log Analytics Workspace. Query in Azure Portal:

```kql
AppServiceConsoleLogs
| where TimeGenerated > ago(1h)
| project TimeGenerated, ResultDescription
| order by TimeGenerated desc
```

### Health Check

Test the health endpoint:

```bash
curl https://<app-service-name>.azurewebsites.net/health
```

Expected response:
```json
{"status": "healthy"}
```

## Accessing the Application

After deployment, access your application at:

```
https://<app-service-name>.azurewebsites.net
```

Example:
```
https://app-agentic-devops.azurewebsites.net
```

### Custom Domain (Optional)

To use a custom domain:

1. **Add custom domain** in Azure Portal
2. **Validate domain** ownership
3. **Configure SSL** certificate (free managed certificate available)

## Scaling

### Vertical Scaling

Change App Service Plan SKU in `infra/variables.tf`:

```hcl
variable "app_service_plan_sku" {
  default = "P2v3"  # More CPU/memory
}
```

Then run `terraform apply`.

### Horizontal Scaling

App Service supports auto-scaling based on:
- CPU percentage
- Memory percentage
- HTTP queue length
- Custom metrics

Configure in Azure Portal: **Settings → Scale out (App Service plan)**

## Troubleshooting

### Container fails to start

**Symptoms**: App Service shows "Application Error"

**Solutions**:
1. Check container logs:
   ```bash
   az webapp log tail --resource-group <rg> --name <app>
   ```

2. Verify image exists in ACR:
   ```bash
   az acr repository show-tags --name <acr> --repository agentic-devops-starter
   ```

3. Validate Dockerfile locally:
   ```bash
   docker build -f app/Dockerfile.appservice -t test .
   docker run -p 8080:8080 test
   ```

### Health check fails

**Symptoms**: Deployment workflow fails at health check step

**Solutions**:
1. Ensure backend is running on port 5100
2. Ensure nginx is proxying to backend
3. Check supervisor logs:
   ```bash
   az webapp log tail --resource-group <rg> --name <app> | grep supervisor
   ```

### 502 Bad Gateway

**Symptoms**: nginx returns 502 when accessing `/api/*`

**Solutions**:
1. Backend may not be started
2. Check backend logs for errors
3. Verify backend is listening on 127.0.0.1:5100

### Managed Identity authentication fails

**Symptoms**: `DefaultAzureCredential` fails to get token

**Solutions**:
1. Verify managed identity is enabled:
   ```bash
   az webapp identity show --resource-group <rg> --name <app>
   ```

2. Check role assignments:
   ```bash
   az role assignment list --assignee <principal-id>
   ```

3. Ensure `AZURE_TENANT_ID` is set in app settings

## Cost Optimization

Current configuration uses:
- **App Service Plan (P1v3)**: ~$100/month
- **ACR (Standard)**: ~$20/month
- **Log Analytics**: ~$10-15/month

**Total**: ~$130-135/month

### Cost Reduction Tips

1. **Use B-series for development**: Change to `B2` (~$55/month)
2. **Enable auto-scale**: Scale down during off-hours
3. **Use Basic ACR for small projects**: ~$5/month
4. **Reduce Log Analytics retention**: Set to 7 days

## Security Considerations

- ✅ **HTTPS-only**: Enforced by default
- ✅ **Managed Identity**: No stored credentials
- ✅ **Private ACR**: Only accessible via managed identity
- ✅ **Security headers**: Added by nginx
- ✅ **CORS configuration**: Configurable via environment variables
- ✅ **Container scanning**: Available in ACR Premium tier

## Next Steps

1. ✅ Deploy infrastructure with Terraform
2. ✅ Configure GitHub Secrets
3. ✅ Push to main branch to trigger deployment
4. ✅ Verify application is running
5. ⬜ (Optional) Configure custom domain
6. ⬜ (Optional) Set up auto-scaling rules
7. ⬜ (Optional) Configure monitoring alerts

## Support

For issues:
- Check App Service logs: `az webapp log tail`
- Review GitHub Actions workflow logs
- Verify Terraform outputs: `terraform output`
- Check Azure Portal for resource status
