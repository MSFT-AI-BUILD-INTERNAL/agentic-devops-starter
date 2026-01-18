# Kubernetes Deployment Configuration

This directory contains Kubernetes manifests for deploying the Agentic DevOps Starter application to Azure Kubernetes Service (AKS) with HTTPS support.

## Files

- **deployment.yaml**: Defines the Kubernetes Deployment for the application with 2 replicas
- **service.yaml**: Defines a ClusterIP Service for internal routing (Ingress handles external access)
- **ingress.yaml**: Defines Ingress resource with TLS/HTTPS configuration (for domain-based access)
- **ingress-ip.yaml**: Defines Ingress resource for IP-based HTTP access (without TLS)
- **cert-issuer.yaml**: Defines cert-manager ClusterIssuers for automatic TLS certificate management

## Deployment Options

### Option 1: HTTPS with Domain (Recommended for Production)

If you have a domain name, the deployment will automatically configure HTTPS with a free Let's Encrypt certificate.

**Required Secrets:**
- `DOMAIN_NAME`: Your domain name (e.g., `app.yourdomain.com`)
- `LETSENCRYPT_EMAIL`: Email for certificate notifications

### Option 2: HTTP with IP Address (For Testing)

If you don't have a domain yet, the deployment will use IP-based access over HTTP.

**Note:** HTTPS requires a domain name for certificate validation. You cannot use HTTPS with only an IP address.

## Prerequisites

Before deploying, ensure you have:

1. **Azure Container Registry (ACR)** - To store Docker images
2. **Azure Kubernetes Service (AKS)** - Target deployment cluster

   **Recommended**: Use the Terraform infrastructure code in the `/infra` directory to create these resources:
   ```bash
   cd infra
   terraform init
   terraform apply
   ```
   See `/infra/README.md` for detailed instructions.

3. **Domain Name** - A domain name that you can configure DNS for (e.g., `app.yourdomain.com`)

4. **GitHub Secrets** configured in your repository:
   - `ACR_NAME`: Name of your Azure Container Registry (from Terraform output)
   - `AKS_CLUSTER_NAME`: Name of your AKS cluster (from Terraform output)
   - `AKS_RESOURCE_GROUP`: Azure resource group containing the AKS cluster (from Terraform output)
   - `AZURE_CLIENT_ID`: **Application (client) ID** of the GitHub Actions service principal
     - ⚠️ **NOT** the AKS Managed Identity or Kubelet Identity
     - This is the App ID from the Azure AD application created for GitHub Actions OIDC
     - See `.github/AZURE_SETUP.md` for setup instructions
   - `AZURE_TENANT_ID`: Azure tenant ID
   - `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
   - `DOMAIN_NAME`: Your domain name (e.g., `app.yourdomain.com`)
   - `LETSENCRYPT_EMAIL`: Email for Let's Encrypt certificate notifications
   - `AZURE_AI_PROJECT_ENDPOINT`: (Optional) Azure AI endpoint
   - `AZURE_AI_MODEL_DEPLOYMENT_NAME`: (Optional) Azure AI model deployment name
   - `OPENAI_API_KEY`: (Optional) OpenAI API key

## HTTPS Setup

The application uses the following components for HTTPS:

1. **NGINX Ingress Controller**: Routes external HTTPS traffic to internal services
2. **cert-manager**: Automatically provisions and manages TLS certificates from Let's Encrypt
3. **Let's Encrypt**: Free, automated certificate authority

### How It Works

1. NGINX Ingress Controller is installed in the `ingress-nginx` namespace
2. cert-manager is installed in the `cert-manager` namespace
3. A ClusterIssuer (`letsencrypt-prod`) is created to request certificates from Let's Encrypt
4. The Ingress resource references the ClusterIssuer to automatically provision a TLS certificate
5. Traffic is automatically redirected from HTTP to HTTPS

### DNS Configuration

After deployment, you need to configure your DNS:

1. Get the Ingress Controller LoadBalancer IP:
   ```bash
   kubectl get service -n ingress-nginx ingress-nginx-controller
   ```

2. Create an A record in your DNS provider:
   - Name: `app` (or your subdomain)
   - Type: `A`
   - Value: `<INGRESS_IP>` (from step 1)
   - TTL: `300` (5 minutes)

3. Wait for DNS propagation (usually 5-15 minutes)

4. Access your application at `https://app.yourdomain.com`

## GitHub Actions Workflow

The deployment is automated via the `.github/workflows/deploy.yml` workflow, which:

1. **Build and Push Job**:
   - Checks out code
   - Authenticates to Azure
   - Logs in to ACR
   - Builds Docker images for backend and frontend
   - Pushes images to ACR with tags (SHA and latest)

2. **Deploy Job**:
   - Authenticates to Azure
   - Gets AKS credentials
   - Installs NGINX Ingress Controller (if not already installed)
   - Installs cert-manager (if not already installed)
   - Creates/updates Kubernetes secrets for Azure configuration
   - Deploys cert-manager ClusterIssuers for Let's Encrypt
   - Applies Kubernetes manifests with variable substitution
   - Deploys Ingress resource with TLS configuration
   - Waits for deployment rollout
   - Retrieves Ingress external IP

## Manual Deployment

If you need to deploy manually:

```bash
# Login to Azure
az login

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

# Create Kubernetes secret (if needed)
kubectl create secret generic azure-config \
  --from-literal=endpoint="your-azure-endpoint" \
  --from-literal=deployment-name="your-deployment-name" \
  --from-literal=openai-api-key="your-openai-key"

# Deploy application
envsubst < k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml

# Deploy cert-manager ClusterIssuer
envsubst < k8s/cert-issuer.yaml | kubectl apply -f -

# Deploy Ingress
envsubst < k8s/ingress.yaml | kubectl apply -f -

# Check deployment status
kubectl rollout status deployment/agentic-devops-app

# Get Ingress IP
kubectl get service -n ingress-nginx ingress-nginx-controller

# Check Ingress status
kubectl get ingress agentic-devops-ingress

# Check certificate status
kubectl get certificate
```

## Application Configuration

The application uses the following environment variables (configured via Kubernetes secrets):

- `AZURE_AI_PROJECT_ENDPOINT`: Azure AI Foundry endpoint URL
- `AZURE_AI_MODEL_DEPLOYMENT_NAME`: Azure AI model deployment name
- `OPENAI_API_KEY`: OpenAI API key (fallback if Azure AI not configured)

## Resource Limits

The deployment is configured with:
- **Requests**: 256Mi memory, 100m CPU
- **Limits**: 512Mi memory, 500m CPU
- **Replicas**: 2 (for high availability)

## Health Checks

- **Backend Liveness Probe**: HTTP GET on port 5100, path `/health`
- **Backend Readiness Probe**: HTTP GET on port 5100, path `/health`
- **Frontend Liveness Probe**: HTTP GET on port 80, path `/`
- **Frontend Readiness Probe**: HTTP GET on port 80, path `/`

## Accessing the Application

After deployment:

1. Get the Ingress Controller LoadBalancer IP:
   ```bash
   kubectl get service -n ingress-nginx ingress-nginx-controller
   ```

2. Configure your DNS A record to point to the LoadBalancer IP

3. Wait for DNS propagation (5-15 minutes)

4. Access your application at `https://<your-domain-name>`

The application will automatically redirect HTTP to HTTPS.

## Certificate Management

cert-manager will automatically:
- Request a TLS certificate from Let's Encrypt
- Store the certificate in a Kubernetes secret
- Renew the certificate before expiration (every 90 days)

To check certificate status:
```bash
# View certificate resources
kubectl get certificate

# Describe certificate (shows status and events)
kubectl describe certificate agentic-devops-tls

# View certificate details
kubectl get secret agentic-devops-tls -o yaml
```

## Troubleshooting

### View pod logs:
```bash
kubectl logs -l app=agentic-devops --tail=100 -f
```

### Check pod status:
```bash
kubectl get pods -l app=agentic-devops
```

### Describe deployment:
```bash
kubectl describe deployment agentic-devops-app
```

### Check service:
```bash
kubectl describe service agentic-devops-service
```

### Check Ingress:
```bash
kubectl describe ingress agentic-devops-ingress
```

### Check NGINX Ingress Controller:
```bash
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### Check cert-manager:
```bash
kubectl get pods -n cert-manager
kubectl logs -n cert-manager -l app=cert-manager
```

### Certificate Issues:

If the certificate is not being issued:

1. Check certificate status:
   ```bash
   kubectl describe certificate agentic-devops-tls
   ```

2. Check certificate request:
   ```bash
   kubectl get certificaterequest
   kubectl describe certificaterequest <name>
   ```

3. Check ACME challenge:
   ```bash
   kubectl get challenge
   kubectl describe challenge <name>
   ```

4. Verify DNS is pointing to the Ingress LoadBalancer IP

5. Ensure port 80 is accessible (required for HTTP-01 challenge)
