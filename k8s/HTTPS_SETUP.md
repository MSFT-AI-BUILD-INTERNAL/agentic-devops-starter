# HTTPS Setup with Let's Encrypt

This guide explains how to configure HTTPS with Let's Encrypt certificates for the application.

## Architecture

The HTTPS setup uses:
- **NGINX Ingress Controller**: L7 load balancer that handles incoming HTTPS traffic
- **cert-manager**: Automatically provisions and renews Let's Encrypt SSL/TLS certificates
- **Let's Encrypt**: Free, automated certificate authority

Traffic flow:
```
Internet → NGINX Ingress (LoadBalancer) → TLS Termination → ClusterIP Service → Pods
         (HTTPS on 443)                                      (HTTP on 80)
```

## Prerequisites

1. **AKS cluster** deployed and accessible via kubectl
2. **Domain name** that you own and can configure DNS for
3. **Email address** for Let's Encrypt certificate notifications

## Setup Steps

### 1. Install NGINX Ingress Controller and cert-manager

Run the automated setup script:

```bash
cd k8s
./setup-https.sh
```

This script will:
- Install NGINX Ingress Controller (creates a LoadBalancer service)
- Install cert-manager for certificate automation
- Display the NGINX Ingress LoadBalancer IP

### 2. Configure DNS

Point your domain to the NGINX Ingress LoadBalancer IP:

```bash
# Get the LoadBalancer IP
kubectl get service ingress-nginx-controller -n ingress-nginx

# Create an A record in your DNS provider:
# your-domain.com → <LoadBalancer IP>
```

### 3. Update Ingress with Your Domain

Edit `k8s/ingress.yaml` and replace `your-domain.com` with your actual domain:

```yaml
spec:
  tls:
    - hosts:
        - your-actual-domain.com  # Change this
      secretName: agentic-devops-tls
  rules:
    - host: your-actual-domain.com  # Change this
```

### 4. Apply Let's Encrypt Certificate Issuer

Set your email and apply the certificate issuer:

```bash
export LETSENCRYPT_EMAIL=your-email@example.com
envsubst < k8s/cert-issuer.yaml | kubectl apply -f -
```

### 5. Deploy or Update the Ingress

```bash
kubectl apply -f k8s/ingress.yaml
```

### 6. Verify Certificate Provisioning

Check that cert-manager is provisioning the certificate:

```bash
# Check certificate status
kubectl get certificate agentic-devops-tls

# Check certificate request
kubectl describe certificaterequest

# Check cert-manager logs if there are issues
kubectl logs -n cert-manager -l app=cert-manager
```

The certificate should be ready within 2-5 minutes.

### 7. Test HTTPS Access

Once the certificate is ready:

```bash
# Test HTTPS access
curl https://your-domain.com

# Verify certificate
curl -vI https://your-domain.com
```

## Troubleshooting

### Certificate Not Provisioning

```bash
# Check certificate status
kubectl describe certificate agentic-devops-tls

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# Check challenge status
kubectl get challenges
kubectl describe challenges
```

Common issues:
- **DNS not propagated**: Wait 5-10 minutes for DNS changes to propagate
- **HTTP-01 challenge failing**: Ensure port 80 is accessible for Let's Encrypt validation
- **Email invalid**: Verify LETSENCRYPT_EMAIL is set correctly

### NGINX Ingress Not Working

```bash
# Check NGINX Ingress Controller status
kubectl get pods -n ingress-nginx

# Check NGINX Ingress Controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Check ingress resource
kubectl describe ingress agentic-devops-ingress
```

### Using Staging Environment for Testing

For testing, use the staging Let's Encrypt issuer to avoid rate limits:

```yaml
# In k8s/ingress.yaml, change the annotation to:
cert-manager.io/cluster-issuer: letsencrypt-staging
```

The staging issuer creates certificates that browsers will show as untrusted, but it's useful for testing the setup.

## Certificate Renewal

cert-manager automatically renews certificates 30 days before expiration. No manual intervention is required.

To check renewal status:

```bash
kubectl get certificate agentic-devops-tls -o yaml
```

## Cost Considerations

- **NGINX Ingress Controller**: Uses Azure LoadBalancer (~$20-30/month)
- **cert-manager**: Free (runs in your cluster)
- **Let's Encrypt certificates**: Free

Total additional cost: ~$20-30/month for the LoadBalancer

## Removing HTTPS Setup

To remove the HTTPS setup:

```bash
# Delete ingress
kubectl delete -f k8s/ingress.yaml

# Delete cert-manager
kubectl delete -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# Delete NGINX Ingress Controller
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml
```

Then change the service back to LoadBalancer type if needed.

## Additional Resources

- [cert-manager Documentation](https://cert-manager.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Let's Encrypt](https://letsencrypt.org/)
