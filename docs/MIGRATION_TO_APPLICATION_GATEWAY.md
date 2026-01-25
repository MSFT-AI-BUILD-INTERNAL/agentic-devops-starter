# Migration Guide: From L4 Load Balancer to Azure Application Gateway

This document provides a guide for migrating from the previous NGINX Ingress Controller setup to Azure Application Gateway with AGIC.

## Overview

The infrastructure has been updated to use Azure Application Gateway (L7 Load Balancer) instead of the previous NGINX Ingress Controller with L4 Load Balancer setup.

## What Changed?

### Infrastructure
- **Added**: Azure Application Gateway module with VNet and subnets
- **Added**: Application Gateway Ingress Controller (AGIC) as an AKS addon
- **Updated**: AKS configuration to use dedicated subnet
- **Removed**: Manual NGINX Ingress Controller installation from CI/CD

### Kubernetes
- **Updated**: Ingress annotations from NGINX to AGIC format
- **Removed**: cert-manager and Let's Encrypt configuration (SSL now handled at gateway)
- **Changed**: Service type remains ClusterIP (no direct external access)

### CI/CD
- **Removed**: NGINX Ingress Controller installation step
- **Removed**: cert-manager installation step
- **Updated**: Final output to show Application Gateway IP

## Migration Steps

### For New Deployments

1. **Configure Terraform variables** in `terraform.tfvars`:
   ```hcl
   # Existing variables remain the same...
   
   # New Application Gateway variables
   app_gateway_name            = "appgw-agentic-devops"
   app_gateway_public_ip_name  = "pip-appgw-agentic-devops"
   vnet_name                   = "vnet-agentic-devops"
   vnet_address_space          = "10.1.0.0/16"
   appgw_subnet_prefix         = "10.1.0.0/24"
   aks_subnet_prefix           = "10.1.1.0/24"
   app_gateway_sku_name        = "Standard_v2"  # or "WAF_v2"
   app_gateway_sku_tier        = "Standard_v2"  # or "WAF_v2"
   app_gateway_capacity        = 2
   ```

2. **Deploy infrastructure**:
   ```bash
   cd infra
   terraform init
   terraform apply
   ```

3. **Deploy application** (via GitHub Actions or manually):
   ```bash
   kubectl apply -f k8s/service-account.yaml
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

4. **Get Application Gateway IP**:
   ```bash
   kubectl get ingress agentic-devops-ingress
   ```

### For Existing Deployments

⚠️ **Important**: This is a breaking change that requires infrastructure recreation.

1. **Backup your data** (if any persistent volumes exist)

2. **Update your terraform.tfvars** with new Application Gateway variables

3. **Recreate infrastructure**:
   ```bash
   cd infra
   terraform init  # Initialize new module
   terraform apply
   ```
   
   **Note**: Terraform will:
   - Create VNet with subnets
   - Create Application Gateway
   - Update AKS with AGIC addon
   - This will cause a brief downtime (~10-15 minutes)

4. **Update DNS** (if using custom domain):
   - Point your domain to the new Application Gateway public IP
   - Get IP: `terraform output app_gateway_public_ip`

5. **Redeploy application**:
   ```bash
   # Via GitHub Actions (push to main branch)
   git push origin main
   
   # Or manually
   kubectl apply -f k8s/ingress.yaml
   ```

6. **Verify deployment**:
   ```bash
   # Check AGIC is running
   kubectl get pods -n kube-system | grep ingress-azure
   
   # Check Ingress status
   kubectl get ingress agentic-devops-ingress
   
   # Check Application Gateway backend health (Azure Portal)
   ```

## Key Differences

| Aspect | Previous (NGINX) | New (Application Gateway) |
|--------|------------------|---------------------------|
| Load Balancer | L4 (Azure Load Balancer) | L7 (Application Gateway) |
| Ingress Controller | NGINX (manually installed) | AGIC (AKS addon) |
| SSL/TLS | Let's Encrypt via cert-manager | Managed at Application Gateway |
| Cost | ~$20/month (Load Balancer) | ~$140-200/month (App Gateway) |
| Features | Basic load balancing | WAF, path routing, SSL offload |
| Network | Default AKS network | Dedicated VNet with subnets |

## Benefits of Application Gateway

1. **L7 Load Balancing**: Path-based routing, host-based routing
2. **SSL/TLS Termination**: Offload SSL processing from pods
3. **Web Application Firewall**: Optional WAF capabilities
4. **Better Performance**: Optimized for Azure environment
5. **Native Integration**: AGIC automatically configures gateway
6. **Health Monitoring**: Advanced health probes
7. **Autoscaling**: Application Gateway can scale automatically

## Cost Considerations

Application Gateway increases monthly costs by approximately $120-180:
- Previous: ~$190-195/month
- New: ~$315-380/month

This cost provides enterprise-grade L7 load balancing, WAF capabilities, and better performance.

**Cost Optimization Tips:**
- Use `Standard_v2` instead of `WAF_v2` if WAF not needed
- Reduce capacity to 1 instance for development
- Use Azure Reserved Instances for production (up to 30% savings)

## Troubleshooting

### AGIC Pod Not Running
```bash
kubectl get pods -n kube-system | grep ingress-azure
kubectl logs -n kube-system -l app=ingress-azure
```

### Application Gateway Backend Unhealthy
1. Check pod health: `kubectl get pods -l app=agentic-devops`
2. Check service: `kubectl get svc agentic-devops-service`
3. Check backend pools in Azure Portal
4. Verify health probe settings

### Cannot Access Application
1. Verify Ingress status: `kubectl describe ingress agentic-devops-ingress`
2. Check Application Gateway listeners and rules (Azure Portal)
3. Verify NSG rules allow traffic
4. Check Application Gateway public IP: `terraform output app_gateway_public_ip`

## SSL/TLS Configuration

To enable HTTPS:

1. **Upload certificate to Application Gateway** (via Azure Portal or Azure CLI)

2. **Update Ingress manifest**:
   ```yaml
   metadata:
     annotations:
       appgw.ingress.kubernetes.io/ssl-redirect: "true"
   spec:
     tls:
       - secretName: app-gateway-tls-cert
         hosts:
           - your-domain.com
   ```

3. **Apply changes**:
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

## Rollback Plan

If you need to rollback to the previous setup:

1. Keep a backup of your old Terraform state
2. Document your previous configuration
3. Note: Rollback requires infrastructure recreation (downtime expected)

For questions or issues, please refer to:
- [Azure Application Gateway Documentation](https://docs.microsoft.com/azure/application-gateway/)
- [AGIC Documentation](https://azure.github.io/application-gateway-kubernetes-ingress/)
- [Repository Issues](../../issues)

## Support

For assistance with the migration:
- Check the updated documentation in `/infra/README.md` and `/k8s/README.md`
- Review the Terraform plan before applying: `terraform plan`
- Test in a development environment first
- Monitor AGIC logs during migration: `kubectl logs -n kube-system -l app=ingress-azure -f`
