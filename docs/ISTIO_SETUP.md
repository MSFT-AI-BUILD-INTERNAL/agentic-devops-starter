# Istio Ingress Gateway Setup Guide

This guide explains how to set up Istio Ingress Gateway with HTTPS support using Let's Encrypt on Azure Kubernetes Service (AKS).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│            Azure Load Balancer (Layer 4)                         │
│            - Public IP Address                                   │
│            - Port 80 (HTTP) and 443 (HTTPS)                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               Istio Ingress Gateway                              │
│               - Service Type: LoadBalancer                       │
│               - Envoy Proxy for L7 routing                       │
│               - TLS termination                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Istio Gateway Resource                         │
│                   - HTTP (port 80)                               │
│                   - HTTPS (port 443)                             │
│                   - TLS certificate from cert-manager            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Istio VirtualService                                │
│              - Route /api/* → Backend (port 5100)                │
│              - Route /* → Frontend (port 80)                     │
│              - CORS policies                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│         Application Service (ClusterIP)                          │
│         - Frontend: port 80                                      │
│         - Backend: port 5100                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Application Pods                                    │
│              - Frontend Container (Nginx + React)                │
│              - Backend Container (FastAPI)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Why Istio Ingress Gateway?

### Advantages over Application Gateway Ingress Controller (AGIC)

1. **Open Source & Portable**: Istio is cloud-agnostic and can run on any Kubernetes cluster
2. **Advanced Traffic Management**: Fine-grained routing, traffic splitting, and canary deployments
3. **Service Mesh Integration**: Can easily extend to full service mesh capabilities
4. **Better Observability**: Built-in metrics, distributed tracing, and access logs
5. **Cost-Effective**: Uses Azure Load Balancer (L4) instead of Application Gateway (L7)
6. **Kubernetes Native**: Follows Kubernetes Gateway API standards

### Cost Comparison

- **Application Gateway**: ~$140-200/month for Standard_v2
- **Azure Load Balancer**: ~$20-30/month for Standard SKU
- **Savings**: ~$120-170/month (~60-85% cost reduction)

## Quick Setup

### Prerequisites

- AKS cluster with kubectl configured
- Cluster has internet access to download Istio
- (Optional) Email address for Let's Encrypt notifications

### Automated Setup

Run the automated setup script:

```bash
# Set your email for Let's Encrypt (optional)
export LETSENCRYPT_EMAIL=your-email@example.com

# Run the setup script
./k8s/setup-istio-https.sh
```

This script will:
1. Install Istio with Ingress Gateway
2. Install cert-manager for certificate management
3. Deploy Gateway and VirtualService
4. Set up Let's Encrypt certificates (if email provided)
5. Configure HTTPS with automatic certificate renewal

### Manual Setup

#### 1. Install Istio

```bash
# Full deployment (Istio + app + networking)
./k8s/deploy.sh

# Verify installation
kubectl get pods -n istio-system
kubectl get svc istio-ingressgateway -n istio-system
```

#### 2. Install cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=300s
```

#### 3. Deploy Istio Gateway and VirtualService

```bash
# Apply Gateway configuration
kubectl apply -f k8s/istio-gateway.yaml

# Apply VirtualService configuration
kubectl apply -f k8s/istio-virtualservice.yaml

# Verify
kubectl get gateway
kubectl get virtualservice
```

#### 4. Set up HTTPS with Let's Encrypt

```bash
# Set your email
export LETSENCRYPT_EMAIL=your-email@example.com

# Get Istio Ingress Gateway IP
INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Ingress IP: $INGRESS_IP"

# Option 1: Use nip.io for testing (no DNS required)
export DOMAIN_NAME="${INGRESS_IP}.nip.io"

# Option 2: Use your own domain (make sure DNS points to INGRESS_IP)
# export DOMAIN_NAME="yourdomain.com"

# Apply cert-issuer
envsubst < k8s/cert-issuer-istio.yaml | kubectl apply -f -

# Apply certificate
envsubst < k8s/istio-certificate.yaml | kubectl apply -f -

# Check certificate status
kubectl describe certificate agentic-devops-tls -n istio-system
kubectl get secret agentic-devops-tls -n istio-system
```

## Configuration Files

### 1. Istio Gateway (`k8s/istio-gateway.yaml`)

Defines the entry point for traffic:
- **HTTP listener**: Port 80 for HTTP traffic
- **HTTPS listener**: Port 443 with TLS configuration
- Uses certificate from cert-manager (secret: `agentic-devops-tls`)

### 2. VirtualService (`k8s/istio-virtualservice.yaml`)

Defines routing rules:
- Routes `/api/*`, `/health`, `/docs` to backend service (port 5100)
- Routes all other traffic to frontend service (port 80)
- Includes CORS configuration for API endpoints

### 3. Certificate Issuer (`k8s/cert-issuer-istio.yaml`)

Defines Let's Encrypt certificate issuers:
- **Production issuer**: For production certificates
- **Staging issuer**: For testing (avoids rate limits)

### 4. Certificate (`k8s/istio-certificate.yaml`)

Requests TLS certificate from Let's Encrypt:
- Automatically renewed before expiration
- Stored in istio-system namespace
- Used by Istio Gateway for HTTPS

## Accessing Your Application

### Get the Ingress IP

```bash
kubectl get service istio-ingressgateway -n istio-system
```

### Access URLs

- **HTTP**: `http://<INGRESS-IP>`
- **HTTPS**: `https://<INGRESS-IP>.nip.io` (if using nip.io)
- **Custom Domain**: `https://yourdomain.com` (if using custom domain)

### Test the endpoints

```bash
# Frontend
curl http://<INGRESS-IP>/

# Backend health check
curl http://<INGRESS-IP>/health

# Backend API
curl http://<INGRESS-IP>/api/
```

## Enable HTTP to HTTPS Redirect

After certificate is issued, enable automatic redirect from HTTP to HTTPS:

1. Edit `k8s/istio-gateway.yaml`
2. Uncomment the `tls` section under the HTTP server:
   ```yaml
   - port:
       number: 80
       name: http
       protocol: HTTP
     hosts:
       - "*"
     tls:
       httpsRedirect: true  # Uncomment this section
   ```
3. Apply the changes:
   ```bash
   kubectl apply -f k8s/istio-gateway.yaml
   ```

## Using a Custom Domain

### 1. Point DNS to Ingress IP

```bash
# Get the IP
INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Create an A record in your DNS:
# yourdomain.com → <INGRESS-IP>
```

### 2. Update Certificate for Your Domain

```bash
export LETSENCRYPT_EMAIL=your-email@example.com
export DOMAIN_NAME=yourdomain.com

# Update certificate
envsubst < k8s/istio-certificate.yaml | kubectl apply -f -

# Wait for certificate to be issued
kubectl get certificate agentic-devops-tls -n istio-system -w
```

### 3. Access via HTTPS

```bash
curl https://yourdomain.com
```

## Monitoring and Troubleshooting

### Check Istio Components

```bash
# Check Istio pods
kubectl get pods -n istio-system

# Check Istio Ingress Gateway service
kubectl get svc istio-ingressgateway -n istio-system

# View Istio Ingress Gateway logs
kubectl logs -n istio-system -l app=istio-ingressgateway
```

### Check Gateway and VirtualService

```bash
# List gateways
kubectl get gateway

# Describe gateway
kubectl describe gateway agentic-devops-gateway

# List virtual services
kubectl get virtualservice

# Describe virtual service
kubectl describe virtualservice agentic-devops-virtualservice
```

### Check Certificate Status

```bash
# Check certificate
kubectl get certificate -n istio-system

# Describe certificate for detailed status
kubectl describe certificate agentic-devops-tls -n istio-system

# Check if secret is created
kubectl get secret agentic-devops-tls -n istio-system

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

### Common Issues

#### 1. Certificate Not Issued

**Problem**: Certificate status shows "False" or errors

**Solutions**:
- Check cert-manager logs: `kubectl logs -n cert-manager -l app=cert-manager`
- Verify DNS points to correct IP
- Check Let's Encrypt rate limits (use staging issuer for testing)
- Ensure ports 80 and 443 are accessible from internet

#### 2. 404 Not Found

**Problem**: All requests return 404

**Solutions**:
- Check VirtualService configuration: `kubectl describe virtualservice agentic-devops-virtualservice`
- Verify service exists: `kubectl get svc agentic-devops-service`
- Check Gateway configuration: `kubectl describe gateway agentic-devops-gateway`

#### 3. Connection Refused

**Problem**: Cannot connect to Ingress IP

**Solutions**:
- Verify LoadBalancer IP is assigned: `kubectl get svc istio-ingressgateway -n istio-system`
- Check Azure Load Balancer in Azure Portal
- Verify network security groups allow traffic on ports 80 and 443

#### 4. TLS Certificate Errors

**Problem**: Browser shows certificate errors

**Solutions**:
- Wait for certificate to be issued (can take 2-5 minutes)
- Check certificate status: `kubectl get certificate -n istio-system`
- Verify domain name matches certificate
- Check if using staging issuer (not trusted by browsers)

#### 5. Azure Workload Identity Authentication Failures

**Problem**: Backend shows Azure AD authentication errors like:
```
WorkloadIdentityCredential: Microsoft Entra ID error '(unauthorized_client) AADSTS700016: Application with identifier '...' was not found in the directory'
```

**Root Cause**: Istio's sidecar proxy intercepts traffic to Azure's Instance Metadata Service (IMDS), preventing workload identity token exchange.

**Solution**: Add Istio traffic exclusion annotation to the deployment:

```yaml
spec:
  template:
    metadata:
      annotations:
        # Exclude Azure IMDS endpoint from Istio sidecar
        traffic.sidecar.istio.io/excludeOutboundIPRanges: "169.254.169.254/32"
```

This annotation tells Istio to bypass the sidecar proxy for requests to the Azure IMDS endpoint (169.254.169.254), allowing workload identity authentication to work correctly.

**Verification**:
```bash
# Check if annotation is present
kubectl get pod -l app=agentic-devops -o yaml | grep -A 2 excludeOutboundIPRanges

# Check environment variables are set
kubectl exec -it deployment/agentic-devops-app -c backend -- env | grep AZURE

# Check workload identity configuration
kubectl describe serviceaccount agentic-devops-sa
```

**Additional Requirements**:
- Ensure `AZURE_TENANT_ID` is set in the pod's environment (from azure-config secret)
- Verify the service account has the correct `azure.workload.identity/client-id` annotation
- Confirm the pod has the label `azure.workload.identity/use: "true"`

## CI/CD Integration

The GitHub Actions workflow automatically:
1. Installs Istio if not present
2. Installs cert-manager if not present
3. Deploys Gateway and VirtualService
4. Sets up HTTPS with Let's Encrypt (if `LETSENCRYPT_EMAIL` secret is set)

### Required GitHub Secrets

Add to your repository secrets:

```yaml
# Optional: For HTTPS setup
LETSENCRYPT_EMAIL: your-email@example.com

# Optional: For custom domain
DOMAIN_NAME: yourdomain.com
```

If these secrets are not set, the application will be accessible via HTTP only.

## Best Practices

### Security
1. **Always use HTTPS in production**: Enable HTTP to HTTPS redirect
2. **Use production Let's Encrypt issuer**: Staging is for testing only
3. **Keep Istio updated**: Regularly update to latest stable version
4. **Monitor certificate expiration**: cert-manager auto-renews, but monitor for issues

### Performance
1. **Enable access logs**: Already configured in Istio installation
2. **Monitor Istio metrics**: Use Prometheus and Grafana
3. **Configure connection pooling**: Adjust based on your traffic
4. **Use horizontal pod autoscaling**: Scale based on metrics

### Cost Optimization
1. **Use Azure Load Balancer Standard**: More cost-effective than Application Gateway
2. **Monitor data transfer costs**: Istio adds minimal overhead
3. **Use spot node pools**: For non-production environments

## Advanced Configuration

### Traffic Splitting (Canary Deployments)

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: agentic-devops-virtualservice
spec:
  hosts:
    - "*"
  gateways:
    - agentic-devops-gateway
  http:
    - route:
        - destination:
            host: agentic-devops-service-v1
          weight: 90
        - destination:
            host: agentic-devops-service-v2
          weight: 10  # 10% traffic to new version
```

### Request Timeouts

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: agentic-devops-virtualservice
spec:
  http:
    - route:
        - destination:
            host: agentic-devops-service
      timeout: 30s
      retries:
        attempts: 3
        perTryTimeout: 10s
```

### Rate Limiting

Requires additional Istio configuration. See [Istio Rate Limiting](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/).

## Migration from Application Gateway

If migrating from Application Gateway Ingress Controller (AGIC):

1. **Keep both running initially**: Test Istio before removing AGIC
2. **Update DNS gradually**: Use weighted DNS or canary releases
3. **Monitor both**: Compare metrics and performance
4. **Remove AGIC**: After validation, remove Application Gateway resources

## Resources

- [Istio Documentation](https://istio.io/latest/docs/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Azure Load Balancer Documentation](https://learn.microsoft.com/en-us/azure/load-balancer/)
- [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/)

## Support

For issues or questions:
- Check Istio logs: `kubectl logs -n istio-system -l app=istio-ingressgateway`
- Review cert-manager logs: `kubectl logs -n cert-manager -l app=cert-manager`
- Consult [Istio Community](https://istio.io/latest/about/community/)
