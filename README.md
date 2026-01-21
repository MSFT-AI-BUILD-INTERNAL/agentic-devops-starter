# Agentic DevOps Starter

MVP for Agentic DevOps Starter (Compass) - A complete CI/CD solution for deploying Python applications to Azure Kubernetes Service.

## Overview

This repository provides a full-stack DevOps solution for deploying a Python-based conversational AI application to Azure:

- **Application**: FastAPI server with AG-UI protocol support (`/app`)
- **Infrastructure**: Terraform code for ACR, AKS, and Log Analytics (`/infra`)
- **CI/CD**: GitHub Actions workflow for automated deployment (`.github/workflows/deploy.yml`)
- **Kubernetes**: Manifests for container orchestration (`/k8s`)
- **Monitoring**: Azure Log Analytics with Container Insights for comprehensive logging and metrics

## Quick Start

### 1. Set Up Development Environment

```bash
# Initialize environment (installs uv, Terraform, kubectl)
./init.sh

# Activate virtual environment
source .venv/bin/activate
```

### 2. Provision Azure Infrastructure

```bash
# Navigate to infrastructure directory
cd infra

# Configure your settings
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy infrastructure
terraform init
terraform apply

# Note the outputs - you'll need these for GitHub Secrets
terraform output
```

See [`/infra/README.md`](./infra/README.md) for detailed infrastructure documentation.

### 3. Configure GitHub Actions

#### Azure Authentication Setup

Before configuring GitHub Secrets, you need to set up Azure authentication for GitHub Actions using OIDC (OpenID Connect). This provides secure, keyless authentication without storing long-lived secrets.

**📖 Follow the detailed setup guide: [`.github/AZURE_SETUP.md`](.github/AZURE_SETUP.md)**

The guide covers:
- Creating Azure AD Application and Service Principal
- Configuring Federated Identity Credentials for OIDC
- Assigning required Azure roles (Contributor, AcrPush)
- Verifying the setup

#### GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```yaml
# From Terraform outputs
ACR_NAME: <output from terraform>
AKS_CLUSTER_NAME: <output from terraform>
AKS_RESOURCE_GROUP: <output from terraform>

# Azure Authentication (OIDC)
# ⚠️ IMPORTANT: AZURE_CLIENT_ID must be the Application (client) ID from the
#              GitHub Actions service principal, NOT the AKS managed identity!
#              Run: az ad app list --display-name "gh-actions-agentic-devops" --query "[0].appId" -o tsv
AZURE_CLIENT_ID: <github-actions-app-id>
AZURE_TENANT_ID: <your-tenant-id>
AZURE_SUBSCRIPTION_ID: <your-subscription-id>

# Workload Identity Configuration
# This is the managed identity's client ID created by Terraform for AKS pods
# Run: cd infra && terraform output -raw workload_identity_client_id
WORKLOAD_IDENTITY_CLIENT_ID: <workload-identity-client-id>

# Application Configuration (Optional)
AZURE_AI_PROJECT_ENDPOINT: <your-azure-ai-endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME: <your-model-deployment>
AZURE_OPENAI_API_VERSION: <api-version>

# HTTPS Configuration (Optional, for Let's Encrypt)
LETSENCRYPT_EMAIL: <your-email@example.com>
```

**How to get WORKLOAD_IDENTITY_CLIENT_ID:**
```bash
cd infra
terraform output -raw workload_identity_client_id
```

### 4. Configure Azure AD Workload Identity

The application uses **Azure AD Workload Identity** to securely authenticate from AKS pods to Azure services (like Azure AI Foundry) using `DefaultAzureCredential`.

#### Why Workload Identity?

- ✅ **No secrets in pods**: Uses OIDC federation instead of storing credentials
- ✅ **Fine-grained permissions**: Each workload gets its own managed identity
- ✅ **Automatic token refresh**: Azure handles token lifecycle
- ✅ **Best practice**: Recommended by Microsoft for AKS authentication

#### Setup Steps

1. **Infrastructure is already configured** (if you ran `terraform apply`):
   - AKS has OIDC issuer and Workload Identity enabled
   - User-Assigned Managed Identity created
   - Federated credential linked to Kubernetes ServiceAccount

2. **Grant Azure AI permissions to the Managed Identity**:

   ```bash
   # Get the principal ID from Terraform outputs
   cd infra
   PRINCIPAL_ID=$(terraform output -raw workload_identity_principal_id)
   
   # Grant permissions to your Azure AI Foundry project
   az role assignment create \
     --assignee $PRINCIPAL_ID \
     --role "Cognitive Services User" \
     --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<AI_PROJECT_NAME>"
   ```

   **Alternative: Use Azure Portal**
   1. Navigate to your Azure AI Foundry project
   2. Go to **Access control (IAM)** → **Add role assignment**
   3. Select role: **Cognitive Services User** or **Azure AI Developer**
   4. In **Members**, search for the managed identity name:
      ```bash
      terraform output -raw workload_identity_name
      ```
      (e.g., `aks-agentic-devops-workload-identity`)
   5. Click **Review + assign**

3. **Verify the setup**:

   After deploying the application, check pod logs:
   ```bash
   kubectl logs -l app=agentic-devops -c backend --tail=20
   ```

   ✅ Success: You'll see INFO logs with agent responses  
   ❌ Failure: `DefaultAzureCredential failed to retrieve token` error

#### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                  AKS Pod (Backend)                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ServiceAccount: agentic-devops-sa                    │  │
│  │  Label: azure.workload.identity/use: "true"           │  │
│  └───────────────────────────────────────────────────────┘  │
│                         │                                    │
│                         │ DefaultAzureCredential             │
│                         ▼                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Azure Workload Identity Webhook                      │  │
│  │  - Injects Azure token volume                         │  │
│  │  - Sets AZURE_* environment variables                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ OIDC Token Exchange
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          Azure AD Federated Identity Credential             │
│  - Maps K8s ServiceAccount → Managed Identity               │
│  - Issuer: AKS OIDC endpoint                                │
│  - Subject: system:serviceaccount:default:agentic-devops-sa │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         User-Assigned Managed Identity                      │
│  - Has "Cognitive Services User" role on AI project         │
│  - Returns Azure AD access token                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Azure AI Foundry / OpenAI                      │
│  - Validates token                                          │
│  - Allows API calls                                         │
└─────────────────────────────────────────────────────────────┘
```

#### Key Files

- [`k8s/service-account.yaml`](k8s/service-account.yaml) - ServiceAccount with Workload Identity annotations
- [`k8s/deployment.yaml`](k8s/deployment.yaml) - Pod spec using the ServiceAccount
- [`infra/managed-identity/`](infra/managed-identity/) - Terraform module for identity setup
- [`app/agui_server.py`](app/agui_server.py) - Uses `DefaultAzureCredential` for authentication

For troubleshooting Workload Identity issues, see [Troubleshooting](#troubleshooting) section.

### 5. Deploy Application

Push to the `main` branch to trigger automatic deployment:

```bash
git push origin main
```

The GitHub Actions workflow will:
1. Build Docker image with `uv` package manager
2. Push image to Azure Container Registry
3. Deploy to Azure Kubernetes Service
4. Wait for rollout completion

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for detailed deployment documentation.

## Repository Structure

```
.
├── app/                    # Python backend application
│   ├── src/               # Application source code
│   ├── Dockerfile         # Container image definition
│   ├── agui_server.py     # FastAPI server with AG-UI protocol
│   └── pyproject.toml     # Python dependencies (managed by uv)
├── frontend/              # Web-based chatbot UI (NEW)
│   ├── src/              # TypeScript/React source code
│   ├── public/           # Static assets
│   ├── package.json      # Node.js dependencies
│   └── README.md         # Frontend documentation
├── infra/                 # Terraform infrastructure
│   ├── acr/              # Azure Container Registry module
│   ├── aks/              # Azure Kubernetes Service module
│   ├── log-analytics/    # Azure Log Analytics Workspace module
│   └── README.md         # Infrastructure documentation
├── k8s/                   # Kubernetes manifests
│   ├── deployment.yaml   # Application deployment
│   ├── service.yaml      # LoadBalancer service
│   └── README.md         # Kubernetes documentation
├── .github/workflows/     # CI/CD pipelines
│   └── deploy.yml        # Deployment workflow
├── DEPLOYMENT.md          # Deployment guide
└── init.sh               # Environment setup script
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │  Build   │ -> │   Push   │ -> │   Deploy to AKS      │  │
│  │  Image   │    │   to ACR │    │   (kubectl apply)    │  │
│  └──────────┘    └──────────┘    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │    Azure Container Registry (ACR)    │
         │    - Store Docker images             │
         │    - Tag with git SHA + latest       │
         └─────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │  Azure Kubernetes Service (AKS)      │
         │  ┌─────────────┐  ┌─────────────┐   │
         │  │   Pod 1     │  │   Pod 2     │   │
         │  │  (app:5100) │  │  (app:5100) │   │
         │  └─────────────┘  └─────────────┘   │
         │          LoadBalancer :80             │
         └─────────────────────────────────────┘
                           │
                           ▼
         ┌─────────────────────────────────────┐
         │   Azure Log Analytics Workspace      │
         │   - Container logs & metrics         │
         │   - Performance monitoring           │
         │   - Kubernetes events                │
         └─────────────────────────────────────┘
```

## Key Features

- ✅ **Infrastructure as Code**: Terraform for reproducible Azure infrastructure
- ✅ **Modern Python**: Uses `uv` for fast, reliable dependency management
- ✅ **Web-Based Chat UI**: React + TypeScript frontend with real-time streaming
- ✅ **Containerization**: Optimized Docker images with multi-stage builds
- ✅ **CI/CD Automation**: GitHub Actions for automated build and deployment
- ✅ **Kubernetes Orchestration**: High-availability deployment with health checks
- ✅ **Secure Authentication**: 
  - OIDC-based Azure authentication for CI/CD (no stored credentials)
  - Azure AD Workload Identity for pod-to-Azure authentication
  - `DefaultAzureCredential` for seamless Azure service access
- ✅ **Monitoring & Logging**: Azure Log Analytics with Container Insights for comprehensive observability
- ✅ **HTTPS Support**: NGINX Ingress with Let's Encrypt certificates
- ✅ **Comprehensive Docs**: Detailed guides for infrastructure, deployment, and operations

## Documentation

- **[Infrastructure Setup](./infra/README.md)**: Terraform configuration and Azure resources
- **[Deployment Guide](./DEPLOYMENT.md)**: Complete deployment workflow and troubleshooting
- **[Kubernetes Config](./k8s/README.md)**: Kubernetes manifests and operations
- **[Backend API Docs](./app/README.md)**: Python application architecture and usage
- **[Frontend Chatbot UI](./app/frontend/README.md)**: Web interface setup and development (NEW)
- **[Feature Specification](./specs/003-copilotkit-frontend/spec.md)**: Chatbot frontend requirements
- **[Quickstart Guide](./specs/003-copilotkit-frontend/quickstart.md)**: 5-minute setup for chat UI

## Development

### Running Locally with Frontend

The application now includes a web-based chatbot interface for interacting with the AI agent.

#### Backend Setup

```bash
# Initialize environment (installs uv, Terraform, kubectl)
./init.sh

# Activate virtual environment
source .venv/bin/activate

# Configure environment variables
cd app
cp .env.example .env
# Edit .env with your Azure OpenAI or OpenAI API keys

# Run the backend server with uv
uv run agui_server.py
```

The backend server will start at `http://127.0.0.1:5100`

#### Frontend Setup (in a new terminal)

```bash
# Navigate to frontend directory
cd app/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

**Quick Test**: Open http://localhost:5173 in your browser and start chatting with the AI assistant!

### Frontend Development

```bash
cd app/frontend

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run type checking
npm run type-check

# Run linting
npm run lint

# Run tests
npm run test
```

For detailed frontend documentation, see [`/app/frontend/README.md`](./app/frontend/README.md).

### Backend Development

```bash
cd app

# Run with auto-reload (development)
uv run uvicorn agui_server:get_app --reload --host 127.0.0.1 --port 5100 --factory

# Run tests
uv run pytest tests/

### Testing Changes

```bash
# Build Docker image locally
cd app
docker build -t agentic-devops-starter:test .

# Run container
docker run -p 5100:5100 agentic-devops-starter:test
```

## Cost Estimation

Approximate monthly costs for Azure resources (US East region):
- **AKS**: ~$140/month (2 x Standard_D2s_v3 nodes)
- **ACR**: ~$20/month (Standard tier)
- **Load Balancer**: ~$20/month
- **Log Analytics**: ~$10-15/month (~5 GB data ingestion)
- **Total**: ~$190-195/month

See [infra/README.md](./infra/README.md) for cost optimization tips.

## Troubleshooting

Common issues and solutions:

### General Issues
1. **404 Not Found from Ingress**: See [INGRESS_TROUBLESHOOTING.md](./INGRESS_TROUBLESHOOTING.md) for IP-based access setup
2. **Build fails**: Check Dockerfile and dependencies in `pyproject.toml`
3. **Deploy fails**: Verify GitHub Secrets and Azure permissions
4. **Pods not starting**: Check logs with `kubectl logs -l app=agentic-devops -c backend`
5. **Can't access service**: Wait for LoadBalancer IP assignment with `kubectl get svc`

### Azure AD Workload Identity Issues

**Symptom**: `DefaultAzureCredential failed to retrieve a token from the managed identity`

**Solutions**:

1. **Verify Workload Identity is enabled on AKS**:
   ```bash
   az aks show --resource-group rg-agentic-devops --name aks-agentic-devops \
     --query "oidcIssuerProfile.enabled" -o tsv
   # Should output: true
   ```

2. **Check ServiceAccount annotation**:
   ```bash
   kubectl get serviceaccount agentic-devops-sa -o yaml
   # Should show: azure.workload.identity/client-id: <client-id>
   ```

3. **Verify Pod labels and ServiceAccount**:
   ```bash
   kubectl get pod -l app=agentic-devops -o yaml | grep -A 5 "serviceAccountName\|azure.workload.identity"
   # Should show serviceAccountName: agentic-devops-sa
   # Should show label: azure.workload.identity/use: "true"
   ```

4. **Check Azure role assignment**:
   ```bash
   # Get the managed identity principal ID
   cd infra
   PRINCIPAL_ID=$(terraform output -raw workload_identity_principal_id)
   
   # List role assignments
   az role assignment list --assignee $PRINCIPAL_ID --all -o table
   # Should show "Cognitive Services User" role on your AI project
   ```

5. **Verify federated credential**:
   ```bash
   IDENTITY_NAME=$(terraform output -raw workload_identity_name)
   RESOURCE_GROUP=$(terraform output -raw resource_group_name)
   az identity federated-credential list \
     --identity-name $IDENTITY_NAME \
     --resource-group $RESOURCE_GROUP -o table
   # Should show issuer matching AKS OIDC URL
   ```

6. **Check Pod environment variables** (injected by Workload Identity webhook):
   ```bash
   kubectl exec -it deployment/agentic-devops-app -c backend -- env | grep AZURE
   # Should show AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_FEDERATED_TOKEN_FILE
   ```

7. **Restart pods after fixing identity issues**:
   ```bash
   kubectl rollout restart deployment/agentic-devops-app
   kubectl rollout status deployment/agentic-devops-app
   ```

**Symptom**: `ManagedIdentityCredential authentication unavailable`

This usually means the Workload Identity webhook didn't inject the token. Check:
- Pod has label `azure.workload.identity/use: "true"`
- ServiceAccount has annotation `azure.workload.identity/client-id`
- Workload Identity addon is enabled on AKS

For detailed troubleshooting guides, see:
- [INGRESS_TROUBLESHOOTING.md](./INGRESS_TROUBLESHOOTING.md) - Fix 404 errors and Ingress issues
- [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting) - Deployment workflow issues
- [infra/README.md](./infra/README.md#troubleshooting) - Infrastructure problems
- [k8s/README.md](./k8s/README.md#troubleshooting) - Kubernetes operations
- [Azure Workload Identity Docs](https://azure.github.io/azure-workload-identity/docs/troubleshooting.html) - Official troubleshooting guide

## License

See [LICENSE](./LICENSE) file in the repository.

## Contributing

Follow the development workflow:
1. Create feature branch
2. Make changes
3. Test locally
4. Submit pull request
5. Wait for CI/CD checks

## Support

For issues or questions:
- Check documentation in respective README files
- Review GitHub Actions logs for workflow issues
- Check Azure Portal for infrastructure status
- View Kubernetes logs for application issues
