# Application Gateway Quick Reference

## 🚀 Quick Deploy

```bash
# 1. Configure
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars - set acr_name to be globally unique

# 2. Deploy
terraform init
terraform apply  # Takes ~15-20 minutes

# 3. Get Application Gateway IP
terraform output appgw_public_ip
```

## 📋 Post-Deployment Setup

```bash
# 4. Deploy app to AKS
az aks get-credentials --resource-group $(terraform output -raw resource_group_name) --name $(terraform output -raw aks_name)
kubectl apply -f ../k8s/service-account.yaml
kubectl apply -f ../k8s/deployment.yaml
kubectl apply -f ../k8s/service.yaml

# 5. Get AKS LoadBalancer IP
kubectl get service agentic-devops-service

# 6. Update Application Gateway backend
# Edit terraform.tfvars:
# appgw_backend_fqdns = ["<LOADBALANCER-IP>"]
terraform apply

# 7. Test
curl http://$(terraform output -raw appgw_public_ip)
```

## 🔍 Key Terraform Outputs

```bash
terraform output appgw_public_ip         # Access URL
terraform output appgw_name              # Resource name
terraform output vnet_name               # VNet name
terraform output aks_subnet_id           # AKS subnet
terraform output appgw_subnet_id         # App Gateway subnet
```

## 🛠️ Common Tasks

### Check Backend Health
```bash
az network application-gateway show-backend-health \
  --resource-group $(terraform output -raw resource_group_name) \
  --name $(terraform output -raw appgw_name)
```

### Update Backend Pool
```bash
# Edit terraform.tfvars, then:
terraform apply
```

### Enable WAF
```bash
# Edit terraform.tfvars:
# appgw_sku_name = "WAF_v2"
# appgw_sku_tier = "WAF_v2"
terraform apply
```

### Scale Application Gateway
```bash
# Edit terraform.tfvars:
# appgw_capacity = 3  # Change from 2 to 3
terraform apply
```

## 🔧 Troubleshooting

### Backend Unhealthy
```bash
# Check AKS service
kubectl get service agentic-devops-service
kubectl get pods

# Verify backend IP in terraform.tfvars matches service EXTERNAL-IP
kubectl get service agentic-devops-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 502 Bad Gateway
```bash
# Check pod logs
kubectl get pods
kubectl logs <pod-name>

# Check service endpoints
kubectl get endpoints agentic-devops-service
```

### Cannot Access App Gateway
```bash
# Verify public IP is assigned
terraform output appgw_public_ip

# Check NSG rules (shouldn't block 80/443)
az network nsg list --resource-group $(terraform output -raw resource_group_name)
```

## 📚 Documentation

- **Deployment Guide**: [docs/APPLICATION_GATEWAY_SETUP.md](APPLICATION_GATEWAY_SETUP.md)
- **Infrastructure**: [infra/README.md](../infra/README.md)
- **Kubernetes**: [k8s/README.md](../k8s/README.md)

## ⚠️ Important Notes

- **First deployment**: AKS will be recreated due to VNet integration
- **Backend FQDNs**: Initially empty `[]`, update after AKS deployment
- **WAF**: Requires WAF_v2 SKU (additional cost)
- **HTTPS**: Requires SSL certificate upload (see deployment guide)
- **AGIC**: Optional tighter integration (see k8s/ingress-appgw.yaml)

## 🎯 Architecture

```
Internet → App Gateway (Public IP) → Backend Pool → AKS LB → Pods
           ↓ Health Probes
           ↓ HTTP Listener (80)
           ↓ Routing Rules
```

## 💰 Cost Estimate (East US)

- Application Gateway v2: ~$0.246/hour (~$180/month)
- Public IP: ~$0.005/hour (~$3.60/month)
- VNet: Free (within limits)
- **Total**: ~$183/month base + data transfer costs

WAF v2: ~$0.443/hour (~$323/month) + data processing fees

## 🔐 Security

- Application Gateway uses static public IP
- Health probes verify backend availability
- WAF available with WAF_v2 SKU
- SSL/TLS termination supported
- Integration with Azure services via Managed Identity

## 🎓 Learning Resources

- [Azure App Gateway Docs](https://docs.microsoft.com/azure/application-gateway/)
- [AGIC Documentation](https://docs.microsoft.com/azure/application-gateway/ingress-controller-overview)
- [Terraform azurerm Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
