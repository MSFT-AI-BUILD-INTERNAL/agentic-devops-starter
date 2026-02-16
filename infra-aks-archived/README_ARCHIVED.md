# AKS Infrastructure (Archived)

**⚠️ This directory is archived and no longer in use.**

## Migration Notice

This infrastructure has been replaced by Azure App Service with Sidecar containers.

- **Old Architecture**: AKS + Istio + Kubernetes + cert-manager
- **New Architecture**: Azure App Service + Sidecar containers
- **Migration Date**: 2026-02-16

## Why the Change?

The application has been rearchitected from AKS (Azure Kubernetes Service) to Azure App Service for:

1. **Reduced Complexity**: No need to manage Kubernetes clusters, Istio service mesh, or cert-manager
2. **Lower Costs**: Pay only for the App Service instances, not cluster infrastructure
3. **Simplified Operations**: Fewer moving parts to maintain and monitor
4. **Easier Deployment**: Direct container deployment without K8s manifests
5. **Built-in Features**: Azure handles TLS, scaling, and monitoring

## New Infrastructure Location

All active infrastructure is now in:
- **Infrastructure Code**: `/infra-appservice/`
- **Docker Configuration**: `/docker-appservice/`
- **Deployment Workflow**: `.github/workflows/deploy-appservice.yml`
- **Documentation**: `/docs/AZURE_APPSERVICE_DEPLOYMENT.md`

## If You Need to Restore AKS

If you need to restore or reference the old AKS infrastructure:

1. Review the archived files in this directory
2. The Terraform configuration is complete and should work
3. Kubernetes manifests are in `/k8s-archived/`
4. Deployment workflow is in `.github/workflows/deploy-aks-archived.yml`

## Architecture Comparison

| Feature | AKS (Archived) | App Service (Current) |
|---------|----------------|----------------------|
| Container Orchestration | Kubernetes | Azure App Service |
| Service Mesh | Istio | Sidecar containers |
| Ingress | Istio Gateway | Built-in Azure |
| TLS/HTTPS | cert-manager + Let's Encrypt | Azure managed |
| Identity | Workload Identity | Managed Identity |
| Scaling | HPA + Cluster Autoscaler | App Service auto-scale |
| Monitoring | Custom (Prometheus) | Log Analytics |
| Cost | Higher (cluster overhead) | Lower (per-app pricing) |
| Complexity | High | Low |

## Resources Created (Historical)

This infrastructure created:
- AKS Cluster (1-5 nodes, D2s_v3)
- Azure Container Registry
- Virtual Network with subnets
- Log Analytics Workspace
- Managed Identity for Workload Identity
- Network Security Groups

## Archived Components

- `/aks/` - AKS cluster Terraform module
- `/acr/` - Container Registry module
- `/network/` - Virtual network configuration
- `/log-analytics/` - Monitoring workspace
- `/managed-identity/` - Workload identity setup
- `main.tf`, `variables.tf`, `outputs.tf` - Main Terraform files

## Migration Path

If migrating from AKS to App Service:

1. Deploy new App Service infrastructure (`/infra-appservice/`)
2. Build and push container images to new ACR
3. Test the App Service deployment
4. Update DNS/traffic routing
5. Destroy old AKS infrastructure: `terraform destroy`

## Support

For questions about the new architecture:
- See `/docs/AZURE_APPSERVICE_DEPLOYMENT.md`
- See `/infra-appservice/README.md`

For questions about this archived infrastructure:
- Review files in this directory
- Check git history: `git log --follow infra-aks-archived/`
