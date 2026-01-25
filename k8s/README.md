# Kubernetes Deployment Configuration

This directory contains Kubernetes manifests for deploying the Agentic DevOps Starter application to Azure Kubernetes Service (AKS).

## Quick Access via Application Gateway

🚀 **Access your application through Azure Application Gateway (L7 Load Balancer)**

After deploying, get the Application Gateway IP:
```bash
kubectl get ingress agentic-devops-ingress
```

Access your application at: `http://<APPLICATION-GATEWAY-IP>`

**Note:** This uses HTTP by default. For production with HTTPS, configure SSL certificates on the Application Gateway.

## Files

- **deployment.yaml**: Defines the Kubernetes Deployment for the application with 2 replicas
- **service.yaml**: Defines a ClusterIP Service for internal pod communication
- **ingress.yaml**: Defines Application Gateway Ingress with AGIC annotations
- **service-account.yaml**: ServiceAccount for Azure AD Workload Identity

**Note:** The following files are for NGINX Ingress Controller and are no longer used with Application Gateway:
- ~~**cert-issuer.yaml**: Let's Encrypt certificate issuer~~ (use Application Gateway SSL certificates instead)
- ~~**setup-https.sh**: Script to install NGINX Ingress Controller~~ (AGIC is installed via Terraform)

## HTTPS Setup with Application Gateway

### Option 1: Using Azure Application Gateway with SSL Certificate (Recommended) ⭐

This option provides:
- ✅ Native L7 load balancing
- ✅ SSL/TLS termination at the gateway
- ✅ Path-based routing
- ✅ WAF capabilities (with WAF_v2 SKU)
- ✅ Better performance and scalability

**Steps:**

1. **Application Gateway is already provisioned** (via Terraform):
   - Public IP for external access
   - AGIC (Application Gateway Ingress Controller) addon enabled on AKS
   - Virtual network with dedicated subnets

2. **Configure SSL certificate**:

   **Option A: Use Azure Key Vault (Recommended for production)**
   ```bash
   # Upload certificate to Key Vault
   az keyvault certificate import \
     --vault-name <your-keyvault> \
     --name app-gateway-cert \
     --file certificate.pfx
   
   # Configure Application Gateway to use the certificate
   # This can be done via Azure Portal or Terraform
   ```

   **Option B: Upload certificate directly to Application Gateway**
   ```bash
   # Via Azure Portal:
   # 1. Go to Application Gateway → Listeners
   # 2. Create/Edit HTTPS listener
   # 3. Upload certificate (.pfx file)
   ```

3. **Update Ingress manifest for HTTPS**:
   
   Edit `k8s/ingress.yaml` to add SSL configuration:
   ```yaml
   metadata:
     annotations:
       appgw.ingress.kubernetes.io/ssl-redirect: "true"
   spec:
     tls:
       - secretName: app-gateway-tls-cert
         hosts:
           - your-domain.com
   ```

4. **Deploy the Ingress**:
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

5. **Verify setup**:
   ```bash
   kubectl get ingress agentic-devops-ingress
   ```

   Access your app at: `https://your-domain.com` or `https://<APP-GATEWAY-PUBLIC-IP>`

### Option 2: HTTP Only (Development/Testing)

The default configuration uses HTTP without SSL:

1. **Deploy** (already done via GitHub Actions):
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

2. **Get Application Gateway IP**:
   ```bash
   kubectl get ingress agentic-devops-ingress
   ```

3. **Access**: `http://<APP-GATEWAY-IP>`
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

After deployment, get the Application Gateway public IP:

```bash
kubectl get ingress agentic-devops-ingress
```

The application will be accessible at `http://<APP-GATEWAY-PUBLIC-IP>/` (or `https://` if SSL is configured)

## Troubleshooting

### Quick Diagnostics

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

### Common Issues

**Application Gateway not configured?**
- Check AGIC pod status: `kubectl get pods -n kube-system | grep ingress-azure`
- Check AGIC logs: `kubectl logs -n kube-system -l app=ingress-azure --tail=50`
- Verify Ingress resource: `kubectl describe ingress agentic-devops-ingress`

**Can't access via Application Gateway IP?**
- Ensure Application Gateway backend health is OK (check in Azure Portal)
- Verify service is running: `kubectl get svc agentic-devops-service`
- Check pod status: `kubectl get pods -l app=agentic-devops`

**502 Bad Gateway error?**
- Backend pods might not be ready
- Check health probes: `kubectl describe ingress agentic-devops-ingress`
- Verify backend configuration in Azure Portal → Application Gateway

For detailed troubleshooting guides:
- **Deployment Issues**: [DEPLOYMENT.md](../DEPLOYMENT.md#troubleshooting)
- **Infrastructure**: [infra/README.md](../infra/README.md#troubleshooting)
- **Application Gateway**: [Azure Application Gateway Troubleshooting](https://learn.microsoft.com/azure/application-gateway/application-gateway-troubleshooting-502)
