# Kubernetes Deployment Configuration

This directory contains Kubernetes manifests for deploying the Agentic DevOps Starter application to Azure Kubernetes Service (AKS) with Istio Ingress Gateway.

## Quick Access via Istio Ingress Gateway

🚀 **Access your application through Istio Ingress Gateway with Azure Load Balancer and optional HTTPS**

After deploying, get the Istio Ingress Gateway IP:
```bash
kubectl get svc istio-ingressgateway -n istio-system
```

Access your application:
- **HTTP**: `http://<INGRESS-IP>`
- **HTTPS**: `https://<INGRESS-IP>.nip.io` (if Let's Encrypt is configured)
- **Custom Domain**: `https://yourdomain.com` (if custom domain is configured)

**For detailed setup instructions, see [Istio Setup Guide](../docs/ISTIO_SETUP.md)**

## Files

### Core Kubernetes Manifests
- **deployment.yaml**: Defines the Kubernetes Deployment for the application with 2 replicas
- **service.yaml**: Defines a ClusterIP Service for internal pod communication
- **service-account.yaml**: ServiceAccount for Azure AD Workload Identity

### Istio Configuration
- **istio-gateway.yaml**: Defines the Istio Gateway for HTTP and HTTPS traffic
- **istio-virtualservice.yaml**: Defines routing rules for frontend and backend services
- **istio-certificate.yaml**: Certificate resource for Let's Encrypt TLS certificates
- **cert-issuer-istio.yaml**: ClusterIssuer for Let's Encrypt certificate management

### Setup Scripts
- **deploy.sh**: Full deployment script (Istio install → app deploy → Gateway/VirtualService → connectivity verification)
- **setup-istio-https.sh**: Complete setup script for Istio with HTTPS
- **setup-https.sh**: Legacy NGINX Ingress setup script (deprecated)
- **cert-issuer.yaml**: Legacy cert-issuer for NGINX (deprecated)

## Architecture

The application uses **Istio Ingress Gateway** for traffic management:

```
Internet → Azure Load Balancer → Istio Ingress Gateway → VirtualService → ClusterIP Service → Pods
           (L4, Port 80/443)    (L7 Routing, TLS)      (Routing Rules)
```

### Why Istio?

- **Cost-Effective**: Uses Azure Load Balancer (~$20-30/month) vs Application Gateway (~$140-200/month)
- **Advanced Traffic Management**: Traffic splitting, canary deployments, circuit breaking
- **Service Mesh Ready**: Can extend to full service mesh capabilities
- **Cloud Native**: Kubernetes-native configuration
- **Better Observability**: Built-in metrics, tracing, and access logs

## Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
# Set your email for Let's Encrypt (optional)
export LETSENCRYPT_EMAIL=your-email@example.com

# Run the complete setup
./k8s/setup-istio-https.sh
```

This will:
1. Install Istio with Ingress Gateway
2. Install cert-manager
3. Deploy Gateway and VirtualService
4. Set up HTTPS with Let's Encrypt

### Option 2: Manual Setup

See the [Istio Setup Guide](../docs/ISTIO_SETUP.md) for detailed manual setup instructions.

## HTTPS Setup with Let's Encrypt

# Check certificate details:
terraform output certificate_secret_id
terraform output key_vault_name
```

### Using Your Own SSL Certificate

For production, replace the self-signed certificate with your own:

**Option 1: Import Certificate to Key Vault (Recommended)**
```bash
# Get Key Vault name from Terraform output
KEY_VAULT_NAME=$(cd infra && terraform output -raw key_vault_name)

# Import your certificate (.pfx format)
az keyvault certificate import \
  --vault-name $KEY_VAULT_NAME \
  --name app-gateway-ssl-cert \
  --file /path/to/your-certificate.pfx \
  --password "your-pfx-password"

# The Application Gateway will automatically use the updated certificate
```

**Option 2: Use Let's Encrypt or Other CA**
```bash
# Generate certificate using certbot or other tool
certbot certonly --manual --preferred-challenges dns -d yourdomain.com

# Convert to PFX format
openssl pkcs12 -export \
  -out certificate.pfx \
  -inkey privkey.pem \
  -in fullchain.pem

# Import to Key Vault (as shown above)
```

### Disabling HTTPS (Development Only)

To disable HTTPS and use HTTP only:

1. **Update Terraform variables** in `infra/terraform.tfvars`:
   ```hcl
   enable_https = false
   ```

2. **Update Ingress** in `k8s/ingress.yaml`:
   ```yaml
   metadata:
     annotations:
       appgw.ingress.kubernetes.io/ssl-redirect: "false"
   # Remove the tls: section
   ```

3. **Apply changes**:
   ```bash
   cd infra && terraform apply
   kubectl apply -f k8s/ingress.yaml
   ```

## Certificate Management

### Viewing Certificate Information
```bash
# Get certificate details from Key Vault
KEY_VAULT_NAME=$(cd infra && terraform output -raw key_vault_name)
az keyvault certificate show \
  --vault-name $KEY_VAULT_NAME \
  --name app-gateway-ssl-cert

# Check certificate expiration
az keyvault certificate show \
  --vault-name $KEY_VAULT_NAME \
  --name app-gateway-ssl-cert \
  --query "attributes.expires" -o tsv
```

### Certificate Renewal

**For Self-Signed Certificates:**
The certificate is set to auto-renew 30 days before expiration. No manual intervention needed.

**For Imported Certificates:**
```bash
# Import renewed certificate
az keyvault certificate import \
  --vault-name $KEY_VAULT_NAME \
  --name app-gateway-ssl-cert \
  --file /path/to/renewed-certificate.pfx

# Application Gateway will automatically use the updated certificate
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
