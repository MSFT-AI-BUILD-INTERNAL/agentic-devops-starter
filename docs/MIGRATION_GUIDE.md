# Migration Guide: AKS to Azure App Service

This guide helps teams migrate from the old AKS-based architecture to the new Azure App Service with Sidecar containers.

## Table of Contents

1. [Overview](#overview)
2. [Why Migrate?](#why-migrate)
3. [Architecture Comparison](#architecture-comparison)
4. [Prerequisites](#prerequisites)
5. [Migration Steps](#migration-steps)
6. [Rollback Plan](#rollback-plan)
7. [FAQ](#faq)

## Overview

This migration moves the Agentic DevOps application from:
- **From**: Azure Kubernetes Service (AKS) + Istio + cert-manager
- **To**: Azure App Service with Sidecar containers

**Migration Time**: ~2-3 hours
**Downtime**: Minimal (DNS cutover only)

## Why Migrate?

### Cost Savings
- **Old**: ~$190-205/month (AKS cluster + Load Balancer + ACR)
- **New**: ~$70-90/month (App Service + ACR)
- **Savings**: ~$115-120/month (60% reduction)

### Simplified Operations
| Aspect | AKS | App Service |
|--------|-----|-------------|
| Cluster Management | Required | Not needed |
| Kubernetes Expertise | Required | Not needed |
| Service Mesh (Istio) | Manual setup | Built-in sidecar |
| TLS Certificates | cert-manager + Let's Encrypt | Azure managed |
| Scaling | HPA + Cluster Autoscaler | Built-in auto-scale |
| Monitoring | Custom Prometheus/Grafana | Built-in Log Analytics |
| Deployment | kubectl + Helm | Simple restart |

### Same Functionality
✅ Frontend + Backend in single deployment  
✅ Same-Origin (no CORS issues)  
✅ HTTPS with TLS  
✅ Managed Identity authentication  
✅ Azure AI integration  
✅ Monitoring and logging  

## Architecture Comparison

### Current (AKS)
```
Internet → Azure LB → Istio Gateway → K8s Service → Pods (2 containers)
                                                        ↓
                                                 cert-manager → Let's Encrypt
```

### New (App Service)
```
Internet → Azure App Service → Frontend (Nginx:80) → Backend (localhost:5100)
                    ↓
              Azure TLS (automatic)
```

## Prerequisites

Before starting the migration:

- [ ] Azure CLI >= 2.50 installed
- [ ] Terraform >= 1.5.0 installed
- [ ] Contributor access to Azure subscription
- [ ] GitHub repository admin access (for secrets)
- [ ] Backup of current configuration
- [ ] DNS access (if using custom domain)

## Migration Steps

### Phase 1: Deploy New Infrastructure (Parallel)

Deploy App Service infrastructure **without** affecting existing AKS:

```bash
# 1. Clone repository
git clone https://github.com/MSFT-AI-BUILD-INTERNAL/agentic-devops-starter.git
cd agentic-devops-starter

# 2. Switch to App Service branch (if not merged to main)
git checkout main  # Or the branch with App Service code

# 3. Navigate to new infrastructure
cd infra-appservice

# 4. Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars:
# - Set unique acr_name (different from old ACR or use same)
# - Configure location, environment, etc.
nano terraform.tfvars

# 5. Deploy infrastructure
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 6. Save outputs
terraform output > ../migration-outputs.txt
export NEW_ACR=$(terraform output -raw acr_name)
export NEW_WEBAPP=$(terraform output -raw webapp_name)
export NEW_RG=$(terraform output -raw resource_group_name)
```

### Phase 2: Build and Deploy Application

```bash
# 1. Build backend image
cd ..  # Back to project root
az acr build \
  --registry $NEW_ACR \
  --image agenticdevops-backend:latest \
  --file docker-appservice/Dockerfile.backend \
  .

# 2. Build frontend image
az acr build \
  --registry $NEW_ACR \
  --image agenticdevops-frontend:latest \
  --file docker-appservice/Dockerfile.frontend \
  .

# 3. Restart App Service to pull images
az webapp restart \
  --name $NEW_WEBAPP \
  --resource-group $NEW_RG

# 4. Wait for startup
echo "Waiting for App Service to start..."
sleep 90

# 5. Get App Service URL
NEW_URL=$(az webapp show \
  --name $NEW_WEBAPP \
  --resource-group $NEW_RG \
  --query defaultHostName -o tsv)

echo "New App URL: https://$NEW_URL"
```

### Phase 3: Test New Deployment

```bash
# 1. Health check
curl -f https://$NEW_URL/health
# Expected: 200 OK

# 2. API health check
curl -f https://$NEW_URL/api/health
# Expected: 200 OK with JSON response

# 3. Test frontend
open https://$NEW_URL
# Verify chat interface loads and works

# 4. Check logs
az webapp log tail --name $NEW_WEBAPP --resource-group $NEW_RG
# Verify no errors

# 5. Load testing (optional)
# Use your preferred load testing tool
# Verify performance is acceptable
```

### Phase 4: Update CI/CD

```bash
# 1. Update GitHub Secrets (Settings → Secrets and variables → Actions)
# Keep old secrets, add new ones:
# - NEW_ACR_NAME: <new acr name>
# - NEW_RESOURCE_GROUP: <new rg name>
# - NEW_WEBAPP_NAME: <new webapp name>

# 2. Update workflow (if using separate secrets)
# Or rename secrets to match new workflow expectations:
# - ACR_NAME → value from NEW_ACR_NAME
# - RESOURCE_GROUP → value from NEW_RESOURCE_GROUP  
# - WEBAPP_NAME → value from NEW_WEBAPP_NAME

# 3. Test CI/CD
# Make a small change and push to main
# Verify new workflow runs successfully
```

### Phase 5: DNS Cutover (if using custom domain)

If you're using a custom domain:

```bash
# 1. Add custom domain to App Service
az webapp config hostname add \
  --webapp-name $NEW_WEBAPP \
  --resource-group $NEW_RG \
  --hostname yourdomain.com

# 2. Get App Service IP (for A record) or use CNAME
az webapp show \
  --name $NEW_WEBAPP \
  --resource-group $NEW_RG \
  --query inboundIpAddress -o tsv

# 3. Update DNS
# Option A: CNAME record
#   CNAME: yourdomain.com → app-xxx.azurewebsites.net
#
# Option B: A record
#   A: yourdomain.com → <ip from step 2>

# 4. Wait for DNS propagation (5-30 minutes)
# Check: dig yourdomain.com

# 5. Enable HTTPS for custom domain
az webapp config ssl bind \
  --name $NEW_WEBAPP \
  --resource-group $NEW_RG \
  --certificate-thumbprint auto \
  --ssl-type SNI
```

### Phase 6: Verify and Monitor

```bash
# 1. Monitor for 24-48 hours
# - Check application logs
# - Monitor performance metrics
# - Verify no errors

# 2. Compare metrics with old deployment
# - Response times
# - Error rates  
# - Resource usage

# 3. Collect feedback from users
# - Any issues accessing the app?
# - Performance acceptable?
```

### Phase 7: Decommission Old AKS

**⚠️ Only after confirming new deployment is stable!**

```bash
# 1. Scale down AKS (optional safety step)
cd infra-aks-archived
terraform apply -var="aks_node_count=0"
# Wait 24 hours to ensure no issues

# 2. Destroy AKS infrastructure
cd infra-aks-archived
terraform destroy
# Review plan carefully
# Type 'yes' to confirm

# 3. Clean up old GitHub secrets (optional)
# Remove AKS-specific secrets:
# - AKS_CLUSTER_NAME
# - WORKLOAD_IDENTITY_CLIENT_ID
# - LETSENCRYPT_EMAIL
# - DOMAIN_NAME (if not using custom domain)

# 4. Update documentation
# Archive or remove AKS-related docs
```

## Rollback Plan

If you need to rollback to AKS:

### Option 1: Quick Rollback (DNS switch)

If AKS is still running:

```bash
# 1. Switch DNS back to AKS
# Update CNAME/A record to point to Istio Ingress Gateway IP

# 2. Wait for DNS propagation

# 3. Verify old deployment is working
```

### Option 2: Full Restore

If AKS was destroyed:

```bash
# 1. Restore AKS infrastructure
cd infra-aks-archived
mv terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars
terraform init
terraform apply

# 2. Deploy application to AKS
kubectl apply -f k8s-archived/

# 3. Wait for pods to start
kubectl get pods -w

# 4. Update DNS (if needed)
```

## FAQ

### Q: Can I reuse the same ACR?
**A**: Yes! You can use the same ACR name in `terraform.tfvars`. The App Service will pull from the same registry.

### Q: What happens to my data?
**A**: This is a stateless application. No data migration needed. Application state is in external services (Azure AI, etc.)

### Q: Can I run both deployments in parallel?
**A**: Yes! Use different ACR names or deploy to different resource groups. Useful for testing.

### Q: What about the old Dockerfile?
**A**: The old `app/Dockerfile` is kept for backward compatibility. New Dockerfiles are in `docker-appservice/`.

### Q: Do I need to change application code?
**A**: No! The application code is unchanged. Only infrastructure and deployment method changed.

### Q: What about environment variables?
**A**: Configure in Terraform (`app_settings`) or Azure Portal (App Service → Configuration → Application settings).

### Q: How do I access logs?
**A**: Use `az webapp log tail` instead of `kubectl logs`. Logs also in Azure Portal → App Service → Log stream.

### Q: What about scaling?
**A**: Configure in Terraform (`app_service_sku`) or Azure Portal (App Service → Scale up/out).

### Q: Can I use deployment slots?
**A**: Yes! App Service supports deployment slots for blue-green deployments:
```bash
az webapp deployment slot create \
  --name $WEBAPP_NAME \
  --resource-group $RG \
  --slot staging
```

### Q: How do I rollback a deployment?
**A**: Use previous image tags:
```bash
# Tag old image as latest
az acr import \
  --name $ACR_NAME \
  --source $ACR_NAME.azurecr.io/agenticdevops-backend:previous-tag \
  --image agenticdevops-backend:latest \
  --force

# Restart
az webapp restart --name $WEBAPP_NAME --resource-group $RG
```

## Support

For issues during migration:

1. **Check logs**: `az webapp log tail --name <webapp> --resource-group <rg>`
2. **Review troubleshooting**: [AZURE_APPSERVICE_DEPLOYMENT.md](./AZURE_APPSERVICE_DEPLOYMENT.md#monitoring-and-troubleshooting)
3. **Compare configs**: Old vs new infrastructure side-by-side
4. **Open issue**: Include logs and error messages

## Additional Resources

- [Azure App Service Documentation](https://learn.microsoft.com/en-us/azure/app-service/)
- [Sidecar Containers Guide](https://learn.microsoft.com/en-us/azure/app-service/tutorial-custom-container-sidecar)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Deployment Guide](./AZURE_APPSERVICE_DEPLOYMENT.md)
- [Infrastructure README](../infra-appservice/README.md)
