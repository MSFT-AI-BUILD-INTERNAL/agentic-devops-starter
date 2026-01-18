# Kubernetes Deployment Configuration

This directory contains Kubernetes manifests for deploying the Agentic DevOps Starter application to Azure Kubernetes Service (AKS).

## Files

- **deployment.yaml**: Defines the Kubernetes Deployment for the application with 2 replicas
- **service.yaml**: Defines a ClusterIP Service (use with Ingress) or LoadBalancer Service for direct access
- **ingress.yaml**: Defines HTTPS Ingress with automatic TLS certificate (requires NGINX Ingress Controller)
- **cert-issuer.yaml**: Let's Encrypt certificate issuer for automatic TLS certificates
- **setup-https.sh**: Automated script to install NGINX Ingress Controller and cert-manager

## HTTPS Setup

### Option 1: Using NGINX Ingress Controller (Recommended) ⭐

This option provides:
- ✅ Automatic HTTPS with Let's Encrypt certificates
- ✅ HTTP to HTTPS redirect
- ✅ Multiple domains/paths support
- ✅ Better load balancing and caching

**Steps:**

1. **Install NGINX Ingress Controller and cert-manager** (one-time setup):
   ```bash
   cd k8s
   ./setup-https.sh
   ```

2. **Configure your domain**:
   - Point your domain DNS A record to the NGINX Ingress LoadBalancer IP
   - Get the IP: `kubectl get service ingress-nginx-controller -n ingress-nginx`

3. **Update configuration files**:
   
   Edit `k8s/ingress.yaml`:
   ```yaml
   spec:
     tls:
       - hosts:
           - your-domain.com  # Replace with your actual domain
   ```
   
   Set `LETSENCRYPT_EMAIL` GitHub Secret:
   - Go to: Repository Settings → Secrets and variables → Actions
   - Add new secret: `LETSENCRYPT_EMAIL` = `your-email@example.com`

4. **Deploy**:
   ```bash
   # For manual deployment
   export LETSENCRYPT_EMAIL=your-email@example.com
   envsubst < k8s/cert-issuer.yaml | kubectl apply -f -
   kubectl apply -f k8s/ingress.yaml
   
   # Or push to trigger GitHub Actions (will use the secret)
   ```

5. **Verify certificate**:
   ```bash
   kubectl get certificate
   kubectl describe certificate agentic-devops-tls
   ```

   Certificate issuance takes 1-2 minutes. Access your app at: `https://your-domain.com`

### Option 2: LoadBalancer with HTTP Only

If you don't need HTTPS or want to use an external proxy:

1. **Change service type** in `k8s/service.yaml`:
   ```yaml
   spec:
     type: LoadBalancer  # Change from ClusterIP
   ```

2. **Deploy**:
   ```bash
   kubectl apply -f k8s/service.yaml
   ```

3. **Get LoadBalancer IP**:
   ```bash
   kubectl get service agentic-devops-service
   ```

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

3. **GitHub Secrets** configured in your repository:
   - `ACR_NAME`: Name of your Azure Container Registry (from Terraform output)
   - `AKS_CLUSTER_NAME`: Name of your AKS cluster (from Terraform output)
   - `AKS_RESOURCE_GROUP`: Azure resource group containing the AKS cluster (from Terraform output)
   - `AZURE_CLIENT_ID`: **Application (client) ID** of the GitHub Actions service principal
     - ⚠️ **NOT** the AKS Managed Identity or Kubelet Identity
     - This is the App ID from the Azure AD application created for GitHub Actions OIDC
     - See `.github/AZURE_SETUP.md` for setup instructions
   - `AZURE_TENANT_ID`: Azure tenant ID
   - `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
   - `AZURE_AI_PROJECT_ENDPOINT`: (Optional) Azure AI endpoint
   - `AZURE_AI_MODEL_DEPLOYMENT_NAME`: (Optional) Azure AI model deployment name
   - `OPENAI_API_KEY`: (Optional) OpenAI API key

## GitHub Actions Workflow

The deployment is automated via the `.github/workflows/deploy.yml` workflow, which:

1. **Build and Push Job**:
   - Checks out code
   - Authenticates to Azure
   - Logs in to ACR
   - Builds Docker image from `/app` directory
   - Pushes image to ACR with tags (SHA and latest)

2. **Deploy Job**:
   - Authenticates to Azure
   - Gets AKS credentials
   - Creates/updates Kubernetes secrets for Azure configuration
   - Applies Kubernetes manifests with variable substitution
   - Waits for deployment rollout
   - Retrieves service external IP

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

# Get AKS credentials
az aks get-credentials \
  --resource-group $AKS_RESOURCE_GROUP \
  --name $AKS_CLUSTER_NAME

# Create Kubernetes secret (if needed)
kubectl create secret generic azure-config \
  --from-literal=endpoint="your-azure-endpoint" \
  --from-literal=deployment-name="your-deployment-name" \
  --from-literal=openai-api-key="your-openai-key"

# Deploy application
envsubst < k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml

# Check deployment status
kubectl rollout status deployment/agentic-devops-app

# Get service external IP
kubectl get service agentic-devops-service
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

- **Liveness Probe**: HTTP GET on port 5100, path `/`
- **Readiness Probe**: HTTP GET on port 5100, path `/`

## Accessing the Application

After deployment, get the external IP:

```bash
kubectl get service agentic-devops-service
```

The application will be accessible at `http://<EXTERNAL-IP>/`

## Troubleshooting

View pod logs:
```bash
kubectl logs -l app=agentic-devops --tail=100 -f
```

Check pod status:
```bash
kubectl get pods -l app=agentic-devops
```

Describe deployment:
```bash
kubectl describe deployment agentic-devops-app
```

Check service:
```bash
kubectl describe service agentic-devops-service
```
