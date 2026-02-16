# Azure App Service Infrastructure

This directory contains Terraform configuration for deploying the Agentic DevOps application to Azure App Service using the **Sidecar Container** pattern.

## Architecture

The infrastructure provisions:
- **Azure App Service** with Sidecar containers (Frontend + Backend sharing localhost)
- **Azure Container Registry** for Docker images
- **App Service Plan** (Linux, B1 tier)
- **Log Analytics Workspace** for monitoring
- **Managed Identity** for secure Azure resource access

## Quick Start

### 1. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

**Important**: Set a globally unique `acr_name` (alphanumeric, 5-50 chars).

### 2. Deploy

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Build and Deploy Containers

```bash
# Get values from Terraform outputs
ACR_NAME=$(terraform output -raw acr_name)
WEBAPP_NAME=$(terraform output -raw webapp_name)
RESOURCE_GROUP=$(terraform output -raw resource_group_name)

# Build and push images (from project root)
cd ..
az acr build --registry $ACR_NAME --image agenticdevops-backend:latest --file docker-appservice/Dockerfile.backend .
az acr build --registry $ACR_NAME --image agenticdevops-frontend:latest --file docker-appservice/Dockerfile.frontend .

# Restart App Service to pull images
az webapp restart --name $WEBAPP_NAME --resource-group $RESOURCE_GROUP
```

### 4. Verify

```bash
# Get app URL
terraform output app_url

# Check health
curl $(terraform output -raw app_url)/health
```

## Files

- `main.tf` - Core infrastructure resources
- `variables.tf` - Input variables with validation
- `outputs.tf` - Useful outputs after deployment
- `providers.tf` - Terraform and provider configuration
- `terraform.tfvars.example` - Example configuration
- `.gitignore` - Excludes sensitive files

## Key Resources

### App Service Sidecar Configuration

The configuration uses `azapi_resource` and `azapi_update_resource` to set up sidecar containers:

1. **Frontend Container** (isMain=true)
   - Nginx serving React SPA on port 80
   - Proxies `/api/*` to `localhost:5100`
   - Receives external traffic

2. **Backend Container** (isMain=false, sidecar)
   - FastAPI + AG-UI on port 5100
   - Shares localhost with frontend
   - Accessible only via frontend proxy

### Managed Identity

System-assigned managed identity with roles:
- `AcrPull` on Container Registry
- Optional: Azure AI service roles (if configured)

### Security

- HTTPS only
- TLS 1.2 minimum
- CORS restricted to self-domain (no wildcards)
- Client certificate support (optional)
- Remote debugging disabled

## Outputs

After deployment, Terraform provides:

| Output | Description |
|--------|-------------|
| `app_url` | Application URL |
| `acr_name` | Container Registry name |
| `webapp_name` | Web App name |
| `resource_group_name` | Resource Group name |
| `app_logs_command` | Command to view logs |
| `app_restart_command` | Command to restart app |

## Monitoring

View logs:
```bash
az webapp log tail --name $(terraform output -raw webapp_name) --resource-group $(terraform output -raw resource_group_name)
```

Check sidecar containers:
```bash
az rest --method GET \
  --uri "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$(terraform output -raw resource_group_name)/providers/Microsoft.Web/sites/$(terraform output -raw webapp_name)/sitecontainers?api-version=2024-04-01" \
  --query "value[].{name:name, isMain:properties.isMain, image:properties.image}" \
  --output table
```

## Cleanup

```bash
terraform destroy -auto-approve
```

**Warning**: This deletes all resources including the Container Registry and all stored images.

## Documentation

For detailed deployment instructions, see:
- [Azure App Service Deployment Guide](../docs/AZURE_APPSERVICE_DEPLOYMENT.md)

## Differences from AKS Infrastructure

This App Service infrastructure replaces the previous AKS-based deployment with:

| Feature | AKS (Old) | App Service (New) |
|---------|-----------|-------------------|
| Orchestration | Kubernetes | Azure App Service |
| Networking | Istio Service Mesh | Sidecar containers |
| TLS | cert-manager + Let's Encrypt | Built-in Azure certificates |
| Scaling | HPA + Cluster Autoscaler | App Service auto-scaling |
| Identity | Workload Identity | Managed Identity |
| Monitoring | Prometheus/Grafana | Log Analytics |
| Complexity | High (K8s manifests, Istio) | Low (Terraform only) |
| Cost | Higher (cluster + nodes) | Lower (pay per app) |

## Prerequisites

- Azure CLI >= 2.50
- Terraform >= 1.5.0
- Azure subscription with Contributor access

## Support

For issues or questions:
1. Check logs: `az webapp log tail`
2. Review [troubleshooting guide](../docs/AZURE_APPSERVICE_DEPLOYMENT.md#monitoring-and-troubleshooting)
3. Open an issue in the repository
