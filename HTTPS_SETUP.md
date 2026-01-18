# HTTPS Setup Guide

This document provides a comprehensive guide for enabling HTTPS access to your AKS application using the Kubernetes Ingress Controller with automatic certificate management.

## Overview

The application now supports HTTPS access through:
- **NGINX Ingress Controller**: Routes external traffic and handles TLS termination
- **cert-manager**: Automatically provisions and renews TLS certificates from Let's Encrypt
- **Flexible Deployment**: Supports both HTTPS (with domain) and HTTP-only (IP-based) modes

## Quick Start

### Prerequisites

1. **Domain Name**: A domain you control (e.g., `app.yourdomain.com`)
2. **DNS Access**: Ability to create A records in your DNS provider
3. **Email Address**: For Let's Encrypt certificate notifications

### Configuration Steps

1. **Add GitHub Secrets**

   Navigate to your repository: Settings → Secrets and variables → Actions

   Add these two secrets:
   ```
   DOMAIN_NAME: app.yourdomain.com
   LETSENCRYPT_EMAIL: your-email@example.com
   ```

2. **Deploy Application**

   Push to main branch or trigger workflow manually:
   ```bash
   git push origin main
   ```

3. **Configure DNS**

   After deployment completes, get the Ingress LoadBalancer IP from the workflow output or run:
   ```bash
   kubectl get service -n ingress-nginx ingress-nginx-controller
   ```

   Create an A record in your DNS provider:
   - **Name**: `app` (or your subdomain)
   - **Type**: `A`
   - **Value**: `<INGRESS_IP>` (from above)
   - **TTL**: `300` (5 minutes)

4. **Wait for Certificate**

   cert-manager will automatically request a certificate from Let's Encrypt. This usually takes 2-5 minutes.

   Check certificate status:
   ```bash
   kubectl get certificate
   kubectl describe certificate agentic-devops-tls
   ```

5. **Access Your Application**

   Once the certificate is ready, access your application at:
   ```
   https://app.yourdomain.com
   ```

   HTTP requests will automatically redirect to HTTPS.

## Without a Domain (Testing Mode)

If you don't have a domain name yet, the application will deploy with HTTP-only access:

1. **Skip Domain Configuration**

   Don't set `DOMAIN_NAME` and `LETSENCRYPT_EMAIL` secrets

2. **Deploy Application**

   Push to main branch or trigger workflow

3. **Access via IP**

   Get the Ingress LoadBalancer IP:
   ```bash
   kubectl get service -n ingress-nginx ingress-nginx-controller
   ```

   Access your application at:
   ```
   http://<INGRESS_IP>
   ```

## Architecture

```
Internet
    │
    ▼
[Azure Load Balancer]
    │ (ports 80/443)
    ▼
[NGINX Ingress Controller]
    │ (TLS termination)
    │ (HTTP → HTTPS redirect)
    ▼
[ClusterIP Service]
    │
    ▼
[Application Pods]
    │
    ├─→ [Frontend Container:80]
    └─→ [Backend Container:5100]
```

## Certificate Management

### Automatic Renewal

cert-manager automatically renews certificates 30 days before expiration. No manual intervention required.

### Certificate Status

Check certificate details:
```bash
# List all certificates
kubectl get certificate

# Detailed certificate info
kubectl describe certificate agentic-devops-tls

# View certificate secret
kubectl get secret agentic-devops-tls -o yaml
```

### Troubleshooting Certificates

If certificate is not issued:

1. **Check certificate status**:
   ```bash
   kubectl describe certificate agentic-devops-tls
   ```

2. **Check certificate request**:
   ```bash
   kubectl get certificaterequest
   kubectl describe certificaterequest <name>
   ```

3. **Check ACME challenge**:
   ```bash
   kubectl get challenge
   kubectl describe challenge <name>
   ```

4. **Common issues**:
   - DNS not pointing to Ingress IP
   - Port 80 not accessible (required for HTTP-01 challenge)
   - Invalid email format
   - Rate limits from Let's Encrypt (use staging issuer for testing)

### Using Staging Certificates (Testing)

To test certificate issuance without hitting Let's Encrypt rate limits:

1. Edit `k8s/ingress.yaml` and change:
   ```yaml
   cert-manager.io/cluster-issuer: letsencrypt-staging
   ```

2. Apply the change:
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

3. Staging certificates will show as "not trusted" in browsers (this is expected)

4. Once testing is complete, switch back to `letsencrypt-prod`

## Manual Deployment

If deploying manually without GitHub Actions:

```bash
# Set environment variables
export ACR_NAME="your-acr-name"
export AKS_CLUSTER_NAME="your-aks-cluster"
export AKS_RESOURCE_GROUP="your-resource-group"
export IMAGE_TAG="latest"
export DOMAIN_NAME="app.yourdomain.com"
export LETSENCRYPT_EMAIL="your-email@example.com"

# Get AKS credentials
az aks get-credentials \
  --resource-group $AKS_RESOURCE_GROUP \
  --name $AKS_CLUSTER_NAME

# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --wait

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.crds.yaml
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --wait

# Deploy application
envsubst < k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml

# Deploy cert-manager ClusterIssuer
envsubst < k8s/cert-issuer.yaml | kubectl apply -f -

# Deploy Ingress with TLS
envsubst < k8s/ingress.yaml | kubectl apply -f -

# Check status
kubectl rollout status deployment/agentic-devops-app
kubectl get ingress
kubectl get certificate
```

## Monitoring and Logs

### View Ingress Controller Logs

```bash
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=100 -f
```

### View cert-manager Logs

```bash
kubectl logs -n cert-manager -l app=cert-manager --tail=100 -f
```

### View Application Logs

```bash
# Backend logs
kubectl logs -l app=agentic-devops -c backend --tail=100 -f

# Frontend logs
kubectl logs -l app=agentic-devops -c frontend --tail=100 -f
```

## Security Considerations

1. **TLS Version**: NGINX Ingress Controller uses TLS 1.2+ by default
2. **Certificate Validation**: Let's Encrypt certificates are trusted by all major browsers
3. **Automatic Renewal**: Certificates auto-renew 30 days before expiration
4. **HTTPS Redirect**: All HTTP traffic automatically redirects to HTTPS
5. **Secret Management**: Certificates stored as Kubernetes secrets with RBAC protection

## Cost Implications

**Additional monthly costs for HTTPS setup**: ~$0

- NGINX Ingress Controller: Runs on existing AKS nodes (no additional cost)
- cert-manager: Runs on existing AKS nodes (no additional cost)
- Let's Encrypt certificates: Free
- LoadBalancer: Already included with AKS (same as before)

**Note**: The LoadBalancer cost remains the same as the previous setup. We've just added TLS termination and certificate management without additional Azure resource costs.

## Frequently Asked Questions

### Can I use my own certificate?

Yes. Create a Kubernetes secret with your certificate:

```bash
kubectl create secret tls custom-tls \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem
```

Then update `k8s/ingress.yaml` to use your secret:
```yaml
spec:
  tls:
    - hosts:
        - ${DOMAIN_NAME}
      secretName: custom-tls
```

Remove the cert-manager annotation:
```yaml
# Remove this line:
cert-manager.io/cluster-issuer: letsencrypt-prod
```

### Can I use multiple domains?

Yes. Update `k8s/ingress.yaml`:

```yaml
spec:
  tls:
    - hosts:
        - domain1.example.com
        - domain2.example.com
      secretName: multi-domain-tls
  rules:
    - host: domain1.example.com
      http:
        paths: [...]
    - host: domain2.example.com
      http:
        paths: [...]
```

### What happens if certificate renewal fails?

cert-manager will retry automatically. You'll receive email notifications at the configured email address if the certificate is about to expire.

### Can I use a wildcard certificate?

Yes, but it requires DNS-01 challenge instead of HTTP-01. This requires configuring DNS provider credentials in cert-manager. See [cert-manager DNS-01 documentation](https://cert-manager.io/docs/configuration/acme/dns01/).

## Support

For issues or questions:
- Check [k8s/README.md](k8s/README.md) for Kubernetes configuration details
- Review GitHub Actions logs for deployment issues
- Check cert-manager logs for certificate issues
- Verify DNS configuration with `dig` or `nslookup`
