# Kubernetes Manifests (Archived)

**⚠️ This directory is archived and no longer in use.**

## Migration Notice

These Kubernetes manifests have been replaced by Azure App Service Sidecar configuration.

- **Old Deployment**: Kubernetes + Istio service mesh
- **New Deployment**: Azure App Service with Terraform-managed sidecar containers
- **Migration Date**: 2026-02-16

## What Changed?

The application no longer uses Kubernetes. Instead, it runs on Azure App Service with:

- **Sidecar containers**: Frontend (Nginx) and Backend (FastAPI) in one App Service
- **No K8s manifests needed**: Infrastructure managed via Terraform
- **No Istio**: Simple nginx proxy for routing
- **No cert-manager**: Azure handles TLS automatically

## New Deployment Location

All deployment configuration is now in:
- **Infrastructure**: `/infra-appservice/` (Terraform)
- **Container Config**: `/docker-appservice/` (Dockerfiles + nginx)
- **CI/CD**: `.github/workflows/deploy-appservice.yml`

## Archived Files

This directory contains:

### Application Deployment
- `deployment.yaml` - K8s Deployment with 2 replicas (frontend + backend containers)
- `service.yaml` - LoadBalancer service (port 80)
- `service-account.yaml` - Kubernetes service account with workload identity

### Istio Configuration
- `istio-gateway.yaml` - HTTP/HTTPS gateway
- `istio-virtualservice.yaml` - Traffic routing rules
- `istio-destinationrule.yaml` - Load balancing policies

### TLS/HTTPS
- `cert-issuer.yaml` - Let's Encrypt cert issuer (HTTP-01)
- `cert-issuer-istio.yaml` - Istio-specific cert issuer
- `istio-certificate.yaml` - TLS certificate resource

### Scripts
- `deploy.sh` - Manual K8s deployment script
- `setup-https.sh` - HTTPS setup with cert-manager
- `setup-istio-https.sh` - Istio HTTPS configuration
- `fix-connectivity.sh` - Troubleshooting script

## Architecture Comparison

### Old (Kubernetes + Istio)
```
Internet → Azure LB → Istio Gateway → VirtualService → K8s Service → Pods (2 containers)
                                                          ↓
                                                  cert-manager → Let's Encrypt
```

### New (App Service Sidecar)
```
Internet → Azure App Service → Frontend (nginx:80) → Backend (localhost:5100)
                    ↓
              Azure TLS (automatic)
```

## Key Differences

| Aspect | K8s + Istio | App Service |
|--------|-------------|-------------|
| Container orchestration | Kubernetes | Azure App Service |
| Service mesh | Istio with sidecar injection | Native sidecar containers |
| Load balancing | K8s Service + Istio | Azure built-in |
| TLS termination | cert-manager + Let's Encrypt | Azure managed certs |
| Routing | VirtualService + Gateway | Nginx proxy in container |
| Health checks | K8s liveness/readiness probes | App Service health check |
| Scaling | HPA (Horizontal Pod Autoscaler) | App Service auto-scale |
| Identity | Workload Identity | Managed Identity |

## If You Need K8s Deployment

To redeploy using Kubernetes:

1. Deploy AKS infrastructure from `/infra-aks-archived/`
2. Install Istio: `istioctl install`
3. Apply manifests: `kubectl apply -f k8s-archived/`
4. Set up cert-manager for HTTPS
5. Configure DNS to point to Istio Ingress Gateway

See `.github/workflows/deploy-aks-archived.yml` for reference.

## Migration Benefits

Moving to App Service provided:

✅ **Simplicity**: No K8s complexity
✅ **Cost**: Lower infrastructure costs
✅ **Maintenance**: Less operational overhead
✅ **Same functionality**: Frontend + Backend + TLS + Monitoring

## Questions?

For the new deployment:
- `/docs/AZURE_APPSERVICE_DEPLOYMENT.md` - Deployment guide
- `/infra-appservice/README.md` - Infrastructure docs

For K8s history:
- Review files in this directory
- Check git history: `git log --follow k8s-archived/`
