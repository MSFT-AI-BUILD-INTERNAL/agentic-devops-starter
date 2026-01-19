# Kubernetes Ingress Troubleshooting Guide

This guide helps you diagnose and fix common issues with the Kubernetes Ingress configuration, particularly the 404 Not Found error when accessing your application.

## Problem: 404 Not Found When Accessing External IP

### Symptom
When you access the external IP provided by the NGINX Ingress Controller LoadBalancer, you receive a **404 Not Found** error.

### Root Cause
The Ingress configuration requires either:
1. A specific hostname (e.g., `agentic-devops.example.com`) with proper DNS configuration
2. Or a default catch-all rule for IP-based access

### Solution

The `k8s/ingress.yaml` has been updated to support both hostname-based and IP-based access:

```yaml
spec:
  rules:
    # Rule 1: For domain-based access with HTTPS
    - host: agentic-devops.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: agentic-devops-service
                port:
                  number: 80
    
    # Rule 2: Default rule for IP-based access (no hostname required)
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: agentic-devops-service
                port:
                  number: 80
```

## Setup Options

### Option 1: Quick Start - Access via IP (HTTP)

**Best for:** Testing, development, or when you don't have a domain name yet.

1. **Deploy the application:**
   ```bash
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

2. **Get the Ingress external IP:**
   ```bash
   kubectl get ingress agentic-devops-ingress
   ```
   
   Wait until you see an IP address in the `ADDRESS` column:
   ```
   NAME                      CLASS   HOSTS                           ADDRESS          PORTS     AGE
   agentic-devops-ingress    nginx   agentic-devops.example.com     20.123.456.78    80, 443   2m
   ```

3. **Access your application:**
   Open your browser and navigate to: `http://<EXTERNAL-IP>`
   
   Example: `http://20.123.456.78`

**Note:** This method uses HTTP (not HTTPS). SSL/TLS is not enabled for IP-based access.

### Option 2: Production Setup - Custom Domain with HTTPS

**Best for:** Production deployments with automatic SSL certificates.

1. **Install NGINX Ingress Controller and cert-manager:**
   ```bash
   cd k8s
   ./setup-https.sh
   ```

2. **Get the NGINX Ingress LoadBalancer IP:**
   ```bash
   kubectl get service ingress-nginx-controller -n ingress-nginx
   ```
   
   Note the `EXTERNAL-IP` value.

3. **Configure DNS:**
   Create an A record pointing your domain to the external IP:
   ```
   Type: A
   Name: @ (or subdomain like 'app')
   Value: <EXTERNAL-IP from step 2>
   TTL: 3600
   ```

4. **Update Ingress configuration:**
   Edit `k8s/ingress.yaml` and replace `agentic-devops.example.com` with your actual domain:
   ```yaml
   spec:
     tls:
       - hosts:
           - your-domain.com  # Your actual domain
         secretName: agentic-devops-tls
     rules:
       - host: your-domain.com  # Your actual domain
   ```

5. **Configure Let's Encrypt:**
   ```bash
   export LETSENCRYPT_EMAIL=your-email@example.com
   envsubst < k8s/cert-issuer.yaml | kubectl apply -f -
   ```

6. **Enable SSL redirect:**
   Edit `k8s/ingress.yaml` and change:
   ```yaml
   nginx.ingress.kubernetes.io/force-ssl-redirect: "false"
   ```
   to:
   ```yaml
   nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
   ```

7. **Deploy the Ingress:**
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

8. **Wait for certificate issuance (1-2 minutes):**
   ```bash
   kubectl get certificate agentic-devops-tls
   kubectl describe certificate agentic-devops-tls
   ```

9. **Access your application:**
   Navigate to: `https://your-domain.com`

## Verification Steps

### Check Ingress Status
```bash
kubectl get ingress agentic-devops-ingress
kubectl describe ingress agentic-devops-ingress
```

### Check Backend Service
```bash
kubectl get service agentic-devops-service
```

Expected output:
```
NAME                      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
agentic-devops-service    ClusterIP   10.0.123.45     <none>        80/TCP,5100/TCP  5m
```

### Check Pods
```bash
kubectl get pods -l app=agentic-devops
```

All pods should be in `Running` state with `READY 2/2` (both frontend and backend containers).

### Check Pod Logs
```bash
# Frontend (nginx) logs
kubectl logs -l app=agentic-devops -c frontend

# Backend logs
kubectl logs -l app=agentic-devops -c backend
```

### Test Backend Connectivity
```bash
# Port-forward to test backend directly
kubectl port-forward deployment/agentic-devops-app 5100:5100

# In another terminal, test the backend
curl http://localhost:5100/health
```

## Common Issues

### Issue 1: "No endpoints available for service"

**Symptom:** Ingress shows no backend endpoints.

**Solution:**
```bash
# Check if pods are running
kubectl get pods -l app=agentic-devops

# Check if service selector matches pod labels
kubectl get service agentic-devops-service -o yaml | grep selector -A 2
kubectl get pods -l app=agentic-devops --show-labels
```

### Issue 2: Certificate not issuing

**Symptom:** Certificate remains in "Pending" state.

**Solution:**
```bash
# Check cert-manager logs
kubectl logs -n cert-manager deploy/cert-manager

# Check certificate status
kubectl describe certificate agentic-devops-tls

# Verify cert-issuer
kubectl get clusterissuer letsencrypt-prod
kubectl describe clusterissuer letsencrypt-prod
```

### Issue 3: Backend API calls fail (network errors)

**Symptom:** Frontend loads but API calls to `/api/*` fail.

**Root Cause:** The frontend nginx is trying to proxy to `http://127.0.0.1:5100` but the backend container isn't reachable.

**Solution:**
```bash
# Verify both containers are running in the same pod
kubectl get pods -l app=agentic-devops -o jsonpath='{.items[*].spec.containers[*].name}'

# Should show: backend frontend

# Check backend health
kubectl exec -it deployment/agentic-devops-app -c backend -- curl http://localhost:5100/health
```

### Issue 4: SSL redirect loop

**Symptom:** Browser keeps redirecting infinitely.

**Solution:**
Make sure `force-ssl-redirect` is set correctly:
- Set to `"false"` for IP-based HTTP access
- Set to `"true"` only after DNS and certificates are configured

### Issue 5: NGINX Ingress Controller not installed

**Symptom:** Ingress remains in "Pending" state without an external IP.

**Solution:**
```bash
# Check if NGINX Ingress Controller is installed
kubectl get pods -n ingress-nginx

# If not installed, run the setup script
cd k8s
./setup-https.sh

# Or install manually
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

## Alternative: Use LoadBalancer Service Directly

If you prefer not to use Ingress, you can expose the service directly:

1. **Update service type:**
   Edit `k8s/service.yaml`:
   ```yaml
   spec:
     type: LoadBalancer  # Change from ClusterIP
   ```

2. **Apply the change:**
   ```bash
   kubectl apply -f k8s/service.yaml
   ```

3. **Get the LoadBalancer IP:**
   ```bash
   kubectl get service agentic-devops-service
   ```

4. **Access the application:**
   Navigate to: `http://<EXTERNAL-IP>:80`

**Note:** This bypasses the Ingress entirely. You won't get HTTPS or advanced routing features.

## Testing Checklist

- [ ] Pods are running (`kubectl get pods`)
- [ ] Service has ClusterIP (`kubectl get service`)
- [ ] Ingress has external IP (`kubectl get ingress`)
- [ ] DNS points to external IP (if using domain)
- [ ] Can access via IP: `http://<EXTERNAL-IP>`
- [ ] Can access via domain: `http://your-domain.com` (if configured)
- [ ] HTTPS works: `https://your-domain.com` (if configured)
- [ ] Frontend loads successfully
- [ ] API calls work (check browser console)
- [ ] Backend health check passes: `curl http://<EXTERNAL-IP>/api/health`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      Internet                            │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ HTTP(S) Request
                         ▼
┌─────────────────────────────────────────────────────────┐
│              NGINX Ingress Controller                    │
│  - Listens on LoadBalancer External IP                   │
│  - Routes based on Host header and path                  │
│  - Handles SSL/TLS termination                           │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ Routes to Service
                         ▼
┌─────────────────────────────────────────────────────────┐
│         agentic-devops-service (ClusterIP)               │
│  - Port 80 → Pod port 80 (frontend)                      │
│  - Port 5100 → Pod port 5100 (backend)                   │
└────────────────────────┬────────────────────────────────┘
                         │
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Pod (2 containers)                    │
│  ┌──────────────────┐      ┌──────────────────────┐     │
│  │   Frontend       │      │   Backend            │     │
│  │   (nginx:80)     │─────▶│   (FastAPI:5100)     │     │
│  │                  │ proxy│                      │     │
│  │  Serves /        │ /api │  Serves /health      │     │
│  │  Proxies /api/*  │      │  Serves /v1/...      │     │
│  └──────────────────┘      └──────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## Key Points

1. **The Ingress needs rules:** Without proper rules, requests won't be routed to the backend service.

2. **Host header matters:** When accessing by IP, no Host header is sent (or it's the IP itself), so you need a catch-all rule without a hostname.

3. **Two-container architecture:** The frontend nginx container proxies `/api/*` requests to the backend container on `localhost:5100` within the same pod.

4. **SSL redirect:** Only enable SSL redirect after you have a domain and valid certificate. For IP access, keep it disabled.

## Support

For additional help:
- Check [k8s/README.md](./k8s/README.md) for Kubernetes configuration details
- Review [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment workflow
- Inspect logs: `kubectl logs -l app=agentic-devops --all-containers=true`
- Check events: `kubectl get events --sort-by='.lastTimestamp'`
