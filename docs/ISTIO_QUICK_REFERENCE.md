# Istio Ingress Gateway - Quick Reference

This is a quick reference guide for the Istio Ingress Gateway implementation. For detailed documentation, see [ISTIO_SETUP.md](./ISTIO_SETUP.md).

## What Was Changed

### New Files Added

1. **k8s/install-istio.sh** - Automated Istio installation script
2. **k8s/setup-istio-https.sh** - Complete Istio + HTTPS setup script
3. **k8s/istio-gateway.yaml** - Istio Gateway configuration (HTTP/HTTPS)
4. **k8s/istio-virtualservice.yaml** - Traffic routing rules
5. **k8s/istio-certificate.yaml** - Let's Encrypt certificate request
6. **k8s/cert-issuer-istio.yaml** - Let's Encrypt certificate issuer
7. **docs/ISTIO_SETUP.md** - Complete Istio setup and troubleshooting guide

### Modified Files

1. **k8s/service.yaml** - Changed from `LoadBalancer` to `ClusterIP`
2. **.github/workflows/deploy.yml** - Added Istio and cert-manager installation steps
3. **README.md** - Updated architecture diagram and documentation links
4. **k8s/README.md** - Updated with Istio information

## Quick Start

### For CI/CD (GitHub Actions)

The workflow now automatically:
1. Installs Istio if not present
2. Installs cert-manager if not present
3. Deploys Gateway and VirtualService

**Optional: Add GitHub Secrets for HTTPS**
```
LETSENCRYPT_EMAIL=your-email@example.com
DOMAIN_NAME=yourdomain.com  # Optional, defaults to <IP>.nip.io
```

### For Manual Setup

```bash
# Connect to your AKS cluster
az aks get-credentials --resource-group <RG> --name <AKS-NAME>

# Option 1: Automated setup with HTTPS
export LETSENCRYPT_EMAIL=your-email@example.com
./k8s/setup-istio-https.sh

# Option 2: Install Istio only (without HTTPS)
./k8s/install-istio.sh
kubectl apply -f k8s/istio-gateway.yaml
kubectl apply -f k8s/istio-virtualservice.yaml
```

## Accessing Your Application

```bash
# Get the Ingress Gateway IP
kubectl get svc istio-ingressgateway -n istio-system

# Access via HTTP
curl http://<INGRESS-IP>

# Access via HTTPS (if configured)
curl https://<INGRESS-IP>.nip.io
```

## Key Components

### 1. Istio Ingress Gateway
- **Namespace**: `istio-system`
- **Service Type**: LoadBalancer (creates Azure Load Balancer)
- **Ports**: 80 (HTTP), 443 (HTTPS)

```bash
# Check status
kubectl get svc istio-ingressgateway -n istio-system
kubectl get pods -n istio-system -l app=istio-ingressgateway
```

### 2. Gateway Resource
- **File**: `k8s/istio-gateway.yaml`
- **Purpose**: Defines entry point for traffic
- **Protocols**: HTTP (port 80), HTTPS (port 443)

```bash
# Check status
kubectl get gateway
kubectl describe gateway agentic-devops-gateway
```

### 3. VirtualService
- **File**: `k8s/istio-virtualservice.yaml`
- **Purpose**: Defines routing rules
- **Routes**:
  - `/api/*`, `/health`, `/docs` → Backend (port 5100)
  - `/*` → Frontend (port 80)

```bash
# Check status
kubectl get virtualservice
kubectl describe virtualservice agentic-devops-virtualservice
```

### 4. Certificate (Optional)
- **File**: `k8s/istio-certificate.yaml`
- **Issuer**: Let's Encrypt (via cert-manager)
- **Namespace**: `istio-system`
- **Secret**: `agentic-devops-tls`

```bash
# Check certificate status
kubectl get certificate -n istio-system
kubectl describe certificate agentic-devops-tls -n istio-system
```

## Common Commands

### Checking Status

```bash
# Check all Istio components
kubectl get all -n istio-system

# Check Gateway and VirtualService
kubectl get gateway,virtualservice

# Check certificate (if HTTPS configured)
kubectl get certificate -n istio-system

# Get Ingress IP
kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Viewing Logs

```bash
# Istio Ingress Gateway logs
kubectl logs -n istio-system -l app=istio-ingressgateway

# Application logs
kubectl logs -l app=agentic-devops -c backend
kubectl logs -l app=agentic-devops -c frontend

# cert-manager logs (if HTTPS configured)
kubectl logs -n cert-manager -l app=cert-manager
```

### Troubleshooting

```bash
# Check if Istio is installed
kubectl get namespace istio-system

# Check if cert-manager is installed
kubectl get namespace cert-manager

# Verify Gateway configuration
kubectl describe gateway agentic-devops-gateway

# Verify VirtualService configuration
kubectl describe virtualservice agentic-devops-virtualservice

# Check certificate issuance (if HTTPS)
kubectl get certificate -n istio-system -w
kubectl describe certificate agentic-devops-tls -n istio-system
```

## Cost Comparison

| Component | Previous (App Gateway) | Current (Istio + LB) | Savings |
|-----------|------------------------|----------------------|---------|
| Ingress | Application Gateway<br/>~$140-200/month | Azure Load Balancer<br/>~$20-30/month | ~$120-170/month |
| **Total Infrastructure** | **~$310-375/month** | **~$190-205/month** | **~$120-170/month (39-45%)** |

## Key Benefits

✅ **60-85% cost reduction** on ingress infrastructure  
✅ **Advanced traffic management** (canary, A/B testing, circuit breaking)  
✅ **Service mesh ready** for future microservices expansion  
✅ **Cloud-agnostic** and portable to any Kubernetes cluster  
✅ **Better observability** with built-in metrics and tracing  
✅ **Kubernetes-native** configuration  

## Migration Notes

### From Application Gateway
- Application Gateway resources can be removed after validation
- DNS should point to new Istio Ingress Gateway IP
- Monitor both systems during transition period

### Backward Compatibility
- All application endpoints remain the same
- No changes required to application code
- Frontend and backend continue to work as before

## Next Steps

1. **Test the deployment**: Verify application is accessible
2. **Configure HTTPS**: Set `LETSENCRYPT_EMAIL` secret if not already done
3. **Point DNS**: Update DNS to point to Istio Ingress Gateway IP
4. **Monitor**: Check logs and metrics for any issues
5. **Cleanup**: Remove old Application Gateway resources (if applicable)

## Documentation Links

- **[Complete Istio Setup Guide](./ISTIO_SETUP.md)** - Detailed setup, configuration, and troubleshooting
- **[Kubernetes README](../k8s/README.md)** - Kubernetes manifests documentation
- **[Main README](../README.md)** - Project overview and getting started

## Support

For issues or questions:
- Check the [Istio Setup Guide](./ISTIO_SETUP.md) troubleshooting section
- Review Istio logs: `kubectl logs -n istio-system -l app=istio-ingressgateway`
- Check cert-manager logs: `kubectl logs -n cert-manager -l app=cert-manager`
- Consult [Istio Documentation](https://istio.io/latest/docs/)
