# GitHub Actions Workflow for Azure App Service Deployment

This document describes the GitHub Actions workflow that deploys the application to Azure App Service via Azure Container Registry (ACR).

## Overview

The workflow automates the following process:
1. Builds a combined frontend + backend Docker image
2. Pushes the image to Azure Container Registry (ACR)
3. Deploys the container to Azure App Service
4. Verifies the deployment health

## Workflow Files

### `.github/workflows/deploy.yml`

A two-job workflow:

**Job 1: build-and-push**
- Checks out code
- Authenticates to Azure using OIDC (Federated Credential)
- Logs in to Azure Container Registry
- Sets up Docker Buildx for efficient builds
- Builds combined container image from `app/Dockerfile.appservice`
- Pushes image with multiple tags (git SHA + latest)
- Uses GitHub Actions cache (`type=gha`) for faster builds

**Job 2: deploy**
- Depends on `build-and-push` job
- Authenticates to Azure via OIDC
- Injects secrets-based app settings (AI endpoints, tenant ID)
- Deploys the container image to App Service using `azure/webapps-deploy@v2`
- Verifies deployment health (5 retries, 10s intervals)
- Outputs application URL and Azure Portal link
- On failure: fetches App Service logs for debugging

### `.github/workflows/ci.yml`

Continuous integration workflow:
- Triggers on push/PR to `main` and `develop` branches
- Runs linting with `ruff`
- Runs tests with `pytest`
- Uses `uv` for dependency management

### `app/Dockerfile.appservice`

Multi-stage build creating a combined container:

```
Stage 1: Frontend build (Node.js 20)
  → npm ci → npm run build → /dist

Stage 2: Backend setup (Python 3.12)
  → uv sync → application code
  → Install nginx + supervisor

Stage 3: Final combined image
  → nginx (:8080) serves frontend + proxies /api/ to backend
  → uvicorn (:5100) runs FastAPI backend
  → supervisor manages both processes
```

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

### Azure Authentication (OIDC)
| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal / App Registration client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |

### Azure Resources (from Terraform outputs)
| Secret | Description |
|--------|-------------|
| `ACR_NAME` | Azure Container Registry name |
| `APP_SERVICE_NAME` | App Service name |
| `RESOURCE_GROUP` | Resource group name |

### Application Configuration (Optional)
| Secret | Description |
|--------|-------------|
| `COPILOT_GITHUB_TOKEN` | GitHub PAT with `copilot` scope for Copilot SDK authentication |

## File Upload via Azure Blob Storage

The deployment provisions an Azure Storage Account that is reachable **only via a private endpoint** from the App Service's integrated subnet. The flow is:

```
Browser ── multipart/form-data ──▶ App Service ── private endpoint ──▶ Blob Storage
                                       │
                                       └── downloads blob ──▶ Copilot SDK session
```

Key infrastructure pieces (all created by Terraform):

| Resource | Purpose |
|----------|---------|
| `module.network` | VNet with two subnets: one delegated to `Microsoft.Web/serverFarms` for App Service VNet integration, one with private-endpoint network policies disabled for the Blob private endpoint |
| `module.app_service` | Has regional VNet integration enabled (`enable_vnet_integration = true`) and `WEBSITE_VNET_ROUTE_ALL=1` so blob traffic only flows over the private endpoint |
| `module.storage` | Storage Account with `public_network_access_enabled = false`, `shared_access_key_enabled = false`, an `uploads` container, blob private endpoint, and `privatelink.blob.core.windows.net` zone linked to the VNet |

> **Role assignments are not managed by Terraform.** See [Manual role assignments](#manual-role-assignments) below.

The backend reads the following app settings (Terraform sets these automatically):

| Setting | Example |
|---------|---------|
| `AZURE_STORAGE_ACCOUNT_NAME` | `stagenticdevops` |
| `AZURE_STORAGE_BLOB_ENDPOINT` | `https://stagenticdevops.blob.core.windows.net` |
| `AZURE_STORAGE_UPLOADS_CONTAINER` | `uploads` |

If none of the storage env vars is present, the `POST /v1/files/upload` endpoint returns HTTP 503 and the frontend hides the attach button — so it is safe to deploy without storage configured (e.g. for local dev).

### Manual role assignments

For security and least-privilege governance, **no `azurerm_role_assignment` resources are managed by Terraform**. After `terraform apply` succeeds, a privileged operator must grant the App Service managed identity the roles it needs. Capture the principal ID first:

```bash
PRINCIPAL_ID=$(az webapp identity show \
  --name <app-service-name> \
  --resource-group <rg> \
  --query principalId -o tsv)
SUB=$(az account show --query id -o tsv)
```

Then grant each role:

```bash
# Pull images from ACR
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "AcrPull" \
  --scope "/subscriptions/$SUB/resourceGroups/<rg>/providers/Microsoft.ContainerRegistry/registries/<acr>"

# Upload/download blobs via managed identity (file-upload feature)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$SUB/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage>"

# Azure AI Foundry access (only if you use AI Foundry)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Azure AI Developer" \
  --scope "<ai-foundry-resource-id>"

az role assignment create --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services User" \
  --scope "<ai-foundry-resource-id>"
```

Record each assignment in `docs/infra-manual-changes.md` per the repo convention.

### Important: plan-time-known toggles

Terraform requires `count` values to be known at plan time. The `enable_vnet_integration` flag on the `app-service` module is a **static boolean**, not derived from other resources' attributes. If you need to disable VNet integration, flip the flag in `infra/main.tf` rather than emptying the related ID input. This avoids the `Invalid count argument` error that occurs when `count` depends on a value not known until apply.

### Resource group: reference vs. create

The resource group is **referenced** (not created) by default — `create_resource_group = false`. Terraform looks up the existing RG via a `data` source. This is the sustainable pattern because:

- Resource groups are typically governed by a separate landing-zone / admin process and pre-exist in the subscription.
- It eliminates the `A resource with the ID ".../resourceGroups/<rg>" already exists` error on re-runs.
- It avoids accidental deletion of the RG (and everything it contains) on `terraform destroy`.

Make sure the RG exists before running `terraform apply`:

```bash
az group create --name <rg> --location <region>
```

For **greenfield deployments** where Terraform should own the RG end-to-end, set `create_resource_group = true` in `terraform.tfvars`. If you previously created it manually and now want Terraform to manage it, import instead: `terraform import 'azurerm_resource_group.main[0]' /subscriptions/<sub>/resourceGroups/<rg>`.

## Workflow Triggers

The deploy workflow runs:
- **Automatically** on push to `main` branch
- **Manually** via `workflow_dispatch` in GitHub Actions UI

## Image Tag Strategy

Images are tagged with:
- `<ACR>.azurecr.io/agentic-devops-starter:<git-sha>` — Specific immutable version (used for deployment)
- `<ACR>.azurecr.io/agentic-devops-starter:latest` — Latest build

## Prerequisites

Before running the workflow:

1. **Create Azure Resources with Terraform**:

   ```bash
   cd infra
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values

   terraform init
   terraform plan
   terraform apply
   ```

   Terraform creates: Resource Group, Virtual Network (with App Service integration + private-endpoint subnets), ACR, App Service Plan, App Service (with regional VNet integration), Log Analytics, and an Azure Storage Account (locked down behind a Blob private endpoint) for file uploads.

   After applying, note the outputs for GitHub Secrets:
   ```bash
   terraform output acr_name
   terraform output app_service_name
   terraform output resource_group_name
   ```

   See [`/infra/README.md`](./infra/README.md) for details.

2. **Set up OIDC Federation**:
   - Create a service principal (App Registration)
   - Configure federated credentials for GitHub Actions
   - Grant `AcrPush` role on the ACR

3. **Configure GitHub Secrets**:
   - Add all required secrets listed above

## Deployment Flow

```
┌─────────────────┐
│ Push to main    │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│ Build Docker Image      │
│ - Frontend (React/Vite) │
│ - Backend (FastAPI/uv)  │
│ - Combined via nginx    │
└────────┬────────────────┘
         │
         v
┌─────────────────────┐
│ Push to ACR         │
│ - Tag with SHA      │
│ - Tag with 'latest' │
└────────┬────────────┘
         │
         v
┌─────────────────────────┐
│ Deploy to App Service   │
│ - Update app settings   │
│ - Deploy container      │
│ - azure/webapps-deploy  │
└────────┬────────────────┘
         │
         v
┌─────────────────────────┐
│ Verify Health           │
│ - curl /health (×5)     │
│ - On failure: show logs │
└─────────────────────────┘
```

## Application Details

The deployed application:
- **External Port**: 8080 (nginx, set via `WEBSITES_PORT`)
- **Internal Port**: 5100 (FastAPI backend, proxied by nginx)
- **URL**: `https://<app-service-name>.azurewebsites.net`
- **Health Endpoint**: `GET /health` → `{"status": "healthy"}`
- **Framework**: FastAPI + AG-UI protocol for conversational AI
- **SSL/TLS**: Managed automatically by Azure App Service

## Configuration Management

Static infrastructure settings (e.g., `WEBSITES_PORT`, `CORS`) are managed by **Terraform** as the single source of truth. The deploy workflow only injects **secrets-based** settings that cannot be stored in Terraform:

| Setting | Managed By | Reason |
|---------|-----------|--------|
| `WEBSITES_PORT` | Terraform | Static infrastructure config |
| `CORS` | Terraform (`site_config.cors`) | Static infrastructure config |
| `GITHUB_TOKEN` | deploy.yml | Copilot SDK auth (from `COPILOT_GITHUB_TOKEN` secret) |

## Troubleshooting

If the workflow fails:

1. **Authentication errors**: Verify OIDC federation and service principal permissions
2. **Build errors**: Check `Dockerfile.appservice` syntax and dependency installation
3. **Push errors**: Ensure ACR permissions (`AcrPush` role) and network connectivity
4. **Deploy errors**: Verify App Service exists and `webapps-deploy` action permissions
5. **Health check fails**: Check container logs:
   ```bash
   az webapp log tail --resource-group <rg> --name <app>
   ```

## Security Considerations

- **OIDC authentication**: No long-lived credentials stored in GitHub
- **Managed Identity**: App Service uses system-assigned identity for ACR and AI access
- **HTTPS enforced**: `https_only = true` on App Service
- **Security headers**: Configured in nginx (X-Content-Type-Options, X-Frame-Options, etc.)
- **Container scanning**: Available in ACR Premium tier

## Monitoring

### View logs
```bash
az webapp log tail --resource-group <rg> --name <app>
```

### Check health
```bash
curl https://<app-service-name>.azurewebsites.net/health
```

### Azure Portal
Navigate to: App Service → **Diagnose and solve problems** or **Log stream**

## Support

For issues or questions:
- Review GitHub Actions logs in the **Actions** tab
- Check App Service logs via Azure CLI or Portal
- See [`docs/APPSERVICE_DEPLOYMENT.md`](./docs/APPSERVICE_DEPLOYMENT.md) for detailed deployment guide
- See [`/app/README.md`](./app/README.md) for application documentation
