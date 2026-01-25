# Application Gateway Deployment Guide

This guide provides step-by-step instructions for deploying Azure Application Gateway with AKS integration.

## Overview

This deployment adds Azure Application Gateway as a Layer 7 load balancer in front of your AKS cluster, providing advanced HTTP/HTTPS routing, SSL termination, and Web Application Firewall capabilities.

## Architecture

```
Internet
    ↓
Azure Application Gateway (Public IP)
    ↓
Backend Pool
    ↓
AKS LoadBalancer Service / Ingress
    ↓
Kubernetes Pods
```

## Prerequisites

- Azure CLI installed and authenticated
- Terraform 1.5.0 or later
- Existing Azure subscription with appropriate permissions

## Deployment Steps

### 1. Configure Variables

Update your `terraform.tfvars` file with the following configuration:

```hcl
# Resource Group Configuration
resource_group_name = "rg-agentic-devops"
location            = "eastus"

# Virtual Network Configuration
vnet_name                     = "vnet-agentic-devops"
vnet_address_space            = ["10.1.0.0/16"]
aks_subnet_name               = "aks-subnet"
aks_subnet_address_prefixes   = ["10.1.0.0/20"]
appgw_subnet_name             = "appgw-subnet"
appgw_subnet_address_prefixes = ["10.1.16.0/24"]

# Application Gateway Configuration
appgw_name           = "appgw-agentic-devops"
appgw_sku_name       = "Standard_v2"
appgw_sku_tier       = "Standard_v2"
appgw_capacity       = 2
appgw_backend_fqdns  = []  # Leave empty for initial deployment

# Azure Container Registry (must be globally unique)
acr_name         = "acragenticdevops123"  # Change this!
acr_sku          = "Standard"
acr_admin_enabled = false

# AKS Configuration
aks_cluster_name    = "aks-agentic-devops"
aks_dns_prefix      = "aks-agentic-devops"
kubernetes_version  = "1.32"
node_count          = 2
vm_size             = "Standard_D2s_v3"
enable_auto_scaling = true
min_node_count      = 1
max_node_count      = 5
```

### 2. Deploy Infrastructure

```bash
# Navigate to infra directory
cd infra

# Initialize Terraform (if not already done)
terraform init

# Review the deployment plan
terraform plan

# Deploy the infrastructure
terraform apply

# Confirm with 'yes' when prompted
```

Expected deployment time: **15-20 minutes**

### 3. Get Application Gateway Public IP

After successful deployment:

```bash
# Get the Application Gateway public IP
terraform output appgw_public_ip

# Example output: 20.12.34.56
```

### 4. Deploy Your Application to AKS

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group $(terraform output -raw resource_group_name) \
  --name $(terraform output -raw aks_name)

# Deploy your application
kubectl apply -f ../k8s/service-account.yaml
kubectl apply -f ../k8s/deployment.yaml
kubectl apply -f ../k8s/service.yaml

# Wait for LoadBalancer service to get an external IP
kubectl get service agentic-devops-service -w
```

### 5. Configure Application Gateway Backend

Once your AKS service has an external IP, update the Application Gateway backend pool:

```bash
# Get the AKS LoadBalancer IP
AKS_LB_IP=$(kubectl get service agentic-devops-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "AKS LoadBalancer IP: $AKS_LB_IP"

# Update terraform.tfvars
# Add the IP to appgw_backend_fqdns:
# appgw_backend_fqdns = ["<AKS_LB_IP>"]

# Apply the change
terraform apply
```

### 6. Test Access

```bash
# Get Application Gateway public IP
APPGW_IP=$(terraform output -raw appgw_public_ip)

# Test HTTP access
curl http://$APPGW_IP

# Or open in browser
echo "Application URL: http://$APPGW_IP"
```

## Post-Deployment Configuration

### Enable HTTPS with SSL Certificate

1. **Generate or obtain SSL certificate**:
```bash
# Self-signed certificate (for testing only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout appgw.key -out appgw.crt \
  -subj "/CN=yourdomain.com"

# Convert to PFX
openssl pkcs12 -export -out appgw.pfx \
  -inkey appgw.key -in appgw.crt \
  -passout pass:YourPassword
```

2. **Upload certificate to Azure Key Vault** (recommended for production)

3. **Update Application Gateway** through Azure Portal or Terraform to add HTTPS listener

### Enable Web Application Firewall (WAF)

To enable WAF protection:

1. Update `terraform.tfvars`:
```hcl
appgw_sku_name = "WAF_v2"
appgw_sku_tier = "WAF_v2"
```

2. Apply changes:
```bash
terraform apply
```

### Configure Custom Domain

1. **Add DNS record** pointing your domain to the Application Gateway public IP
2. **Update backend FQDNs** in terraform.tfvars
3. **Configure SSL certificate** for your domain
4. **Update ingress** annotations in Kubernetes

## Monitoring and Troubleshooting

### Check Backend Health

```bash
# View backend health status
az network application-gateway show-backend-health \
  --resource-group $(terraform output -raw resource_group_name) \
  --name $(terraform output -raw appgw_name)
```

### View Application Gateway Logs

```bash
# Enable diagnostics (one-time setup)
az monitor diagnostic-settings create \
  --name appgw-diagnostics \
  --resource $(terraform output -raw appgw_id) \
  --logs '[{"category": "ApplicationGatewayAccessLog", "enabled": true}]' \
  --workspace $(terraform output -raw log_analytics_workspace_id)
```

### Common Issues

#### Backend Shows Unhealthy
- **Cause**: Application Gateway cannot reach the backend
- **Solution**: 
  - Verify AKS service is running: `kubectl get services`
  - Check backend IP/FQDN is correct
  - Ensure health probe path returns HTTP 200
  - Verify Network Security Groups allow traffic

#### 502 Bad Gateway Error
- **Cause**: Backend service is not responding
- **Solution**:
  - Check AKS pod status: `kubectl get pods`
  - View pod logs: `kubectl logs <pod-name>`
  - Verify service port configuration

#### Cannot Access Application Gateway
- **Cause**: NSG or firewall blocking access
- **Solution**:
  - Verify public IP is correct: `terraform output appgw_public_ip`
  - Check NSG rules on Application Gateway subnet
  - Test with curl or browser

## Cleanup

To remove all resources:

```bash
# Navigate to infra directory
cd infra

# Destroy all infrastructure
terraform destroy

# Confirm with 'yes' when prompted
```

## Next Steps

- [Configure HTTPS with Let's Encrypt](../k8s/README.md)
- [Set up Application Gateway Ingress Controller (AGIC)](https://docs.microsoft.com/azure/application-gateway/ingress-controller-overview)
- [Enable WAF and configure protection rules](https://docs.microsoft.com/azure/web-application-firewall/ag/ag-overview)
- [Configure custom domain and DNS](https://docs.microsoft.com/azure/application-gateway/application-gateway-web-app-overview)

## Resources

- [Azure Application Gateway Documentation](https://docs.microsoft.com/azure/application-gateway/)
- [Application Gateway Components](https://docs.microsoft.com/azure/application-gateway/application-gateway-components)
- [Application Gateway Troubleshooting](https://docs.microsoft.com/azure/application-gateway/application-gateway-troubleshooting-502)
- [Terraform Azure Application Gateway](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/application_gateway)
