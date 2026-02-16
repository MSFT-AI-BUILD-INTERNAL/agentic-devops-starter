# Agentic DevOps Starter

MVP for Agentic DevOps Starter - A complete CI/CD solution for deploying Python applications to Azure App Service.

## Overview

This repository provides a full-stack DevOps solution for deploying a Python-based conversational AI application to Azure:

- **Application**: FastAPI backend with AG-UI protocol + React frontend with AG-UI chat interface
- **Infrastructure**: Terraform code for Azure App Service, ACR, and Log Analytics (`/infra-appservice`)
- **CI/CD**: GitHub Actions workflow for automated deployment (`.github/workflows/deploy-appservice.yml`)
- **Containers**: Sidecar pattern with Frontend (Nginx + React) and Backend (FastAPI) sharing localhost
- **Monitoring**: Azure Log Analytics with App Service diagnostics
- **Security**: HTTPS with Azure-managed certificates, restrictive CORS, managed identity authentication

## Quick Start

### 1. Set Up Development Environment

```bash
# Initialize environment (installs uv and Terraform)
./init.sh

# Activate virtual environment
source .venv/bin/activate
```

### 2. Provision Azure Infrastructure

```bash
# Navigate to App Service infrastructure directory
cd infra-appservice

# Configure your settings
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values (especially acr_name)

# Deploy infrastructure
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Note the outputs - you'll need these for GitHub Secrets
terraform output
```

See [`/infra-appservice/README.md`](./infra-appservice/README.md) for detailed infrastructure documentation.

### 3. Configure GitHub Actions

#### Azure Authentication Setup

Before configuring GitHub Secrets, you need to set up Azure authentication for GitHub Actions using OIDC (OpenID Connect). This provides secure, keyless authentication without storing long-lived secrets.

**📖 Follow the Azure App Service deployment guide: [`/docs/AZURE_APPSERVICE_DEPLOYMENT.md`](./docs/AZURE_APPSERVICE_DEPLOYMENT.md#setting-up-oidc-authentication)**

The guide covers:
- Creating Azure AD Application and Service Principal
- Configuring Federated Identity Credentials for OIDC
- Assigning required Azure roles (Contributor)
- Verifying the setup

#### GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```yaml
# From Terraform outputs
ACR_NAME: <output from terraform>
RESOURCE_GROUP: <output from terraform>
WEBAPP_NAME: <output from terraform>

# Azure Authentication (OIDC)
AZURE_CLIENT_ID: <service-principal-client-id>
AZURE_TENANT_ID: <your-tenant-id>
AZURE_SUBSCRIPTION_ID: <your-subscription-id>

# Application Configuration (Optional)
AZURE_AI_PROJECT_ENDPOINT: <your-azure-ai-endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME: <your-model-deployment>
```

**How to get values:**
```bash
cd infra-appservice
terraform output acr_name
terraform output resource_group_name
terraform output webapp_name
```

### 4. Deploy Application

Push to the `main` branch to trigger automatic deployment:

```bash
git push origin main
```

The GitHub Actions workflow will:
1. Build Frontend Docker image (Nginx + React SPA)
2. Build Backend Docker image (FastAPI + AG-UI)
3. Push images to Azure Container Registry
4. Deploy to Azure App Service using Sidecar pattern
5. Run health checks

See [`/docs/AZURE_APPSERVICE_DEPLOYMENT.md`](./docs/AZURE_APPSERVICE_DEPLOYMENT.md) for detailed deployment documentation.

## Repository Structure

```
.
├── app/                         # Application code
│   ├── src/                    # Python backend source
│   ├── frontend/               # React + TypeScript frontend
│   ├── agui_server.py          # FastAPI server with AG-UI protocol
│   └── pyproject.toml          # Python dependencies (managed by uv)
├── infra-appservice/           # Terraform for Azure App Service (CURRENT)
│   ├── main.tf                 # App Service, ACR, sidecar containers
│   ├── variables.tf            # Configuration variables
│   ├── outputs.tf              # Deployment outputs
│   └── README.md               # Infrastructure documentation
├── docker-appservice/          # Container configuration (CURRENT)
│   ├── Dockerfile.backend      # Backend container
│   ├── Dockerfile.frontend     # Frontend container
│   └── nginx-appservice.conf   # Nginx proxy configuration
├── .github/workflows/          # CI/CD pipelines
│   └── deploy-appservice.yml   # App Service deployment (CURRENT)
├── docs/                       # Documentation
│   └── AZURE_APPSERVICE_DEPLOYMENT.md  # Deployment guide
├── infra-aks-archived/         # Old AKS infrastructure (ARCHIVED)
├── k8s-archived/               # Old Kubernetes manifests (ARCHIVED)
└── init.sh                     # Environment setup script
```

## Architecture

### Current Architecture (Azure App Service + Sidecar)

```
                    ┌─────────────────────────────────────────┐
                    │     Azure App Service (Sidecar Mode)     │
                    │     https://app-xxx.azurewebsites.net     │
   Browser ────────│─────────────────────────────────────────  │
                    │                                          │
                    │  ┌──────────────────────────────────┐    │
                    │  │  frontend (Nginx:80, isMain=true)   │    │
                    │  │    /         → React SPA            │    │
                    │  │    /api/*    → localhost:5100       │    │
                    │  └──────────────────────────────────┘    │
                    │          │ localhost shared (sidecar)     │
                    │  ┌──────────────────────────────────┐    │
                    │  │  backend (uvicorn:5100, sidecar)    │    │
                    │  │    FastAPI + AG-UI                  │    │
                    │  └──────────────────────────────────┘    │
                    └─────────────────────────────────────────┘
                               │
                               ▼
          ┌─────────────────────────────────────┐
          │   Azure Log Analytics Workspace      │
          │   - Application logs & metrics       │
          │   - Container diagnostics            │
          │   - Performance monitoring           │
          └─────────────────────────────────────┘
```

**Key Benefits:**
- **Same-Origin**: Frontend and backend share domain → no CORS issues
- **Simplified**: No Kubernetes, no service mesh, no complex networking
- **Cost-Effective**: Pay only for App Service, no cluster overhead
- **Managed**: Azure handles TLS, scaling, monitoring

### Previous Architecture (AKS + Istio) - ARCHIVED

The previous architecture used Azure Kubernetes Service with Istio service mesh. Files are archived in:
- `/infra-aks-archived/` - AKS Terraform configuration
- `/k8s-archived/` - Kubernetes manifests and Istio configuration

See architecture comparison in [`/infra-aks-archived/README_ARCHIVED.md`](./infra-aks-archived/README_ARCHIVED.md).

## Key Features

- ✅ **Infrastructure as Code**: Terraform for reproducible Azure infrastructure
- ✅ **Modern Python**: Uses `uv` for fast, reliable dependency management
- ✅ **Web-Based Chat UI**: React + TypeScript frontend with AG-UI protocol
- ✅ **Sidecar Architecture**: Frontend and Backend containers share localhost (no CORS)
- ✅ **Containerization**: Optimized Docker images with multi-stage builds
- ✅ **CI/CD Automation**: GitHub Actions for automated build and deployment
- ✅ **Azure App Service**: Managed platform with built-in scaling and TLS
- ✅ **Secure Authentication**: 
  - OIDC-based Azure authentication for CI/CD (no stored credentials)
  - Azure Managed Identity for app-to-Azure authentication
  - `DefaultAzureCredential` for seamless Azure service access
- ✅ **Monitoring & Logging**: Azure Log Analytics with App Service diagnostics
- ✅ **Cost Optimized**: Lower infrastructure costs compared to AKS
- ✅ **Simplified Operations**: No Kubernetes complexity, fewer moving parts
- ✅ **Comprehensive Docs**: Detailed guides for infrastructure, deployment, and operations

## Documentation

- **[Azure App Service Deployment Guide](./docs/AZURE_APPSERVICE_DEPLOYMENT.md)**: Complete App Service deployment workflow
- **[Migration Guide](./docs/MIGRATION_GUIDE.md)**: Step-by-step guide for migrating from AKS to App Service
- **[Infrastructure Setup](./infra-appservice/README.md)**: Terraform configuration and Azure resources
- **[Backend API Docs](./app/README.md)**: Python application architecture and usage
- **[Frontend Chatbot UI](./app/frontend/README.md)**: Web interface setup and development

### Archived Documentation (Previous AKS Architecture)
- [Archived AKS Infrastructure](./infra-aks-archived/README_ARCHIVED.md): Previous Kubernetes setup
- [Archived K8s Manifests](./k8s-archived/README_ARCHIVED.md): Previous deployment configuration

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
- **App Service**: ~$55/month (B1 Basic tier)
- **ACR**: ~$5/month (Basic tier) or ~$20/month (Standard tier)
- **Log Analytics**: ~$10-15/month (~5 GB data ingestion)
- **Total**: ~$70-90/month

**Cost Savings vs AKS**: By using App Service instead of AKS, you save ~$115-120/month (60% cost reduction):
- No cluster infrastructure costs
- No load balancer overhead
- No Istio/cert-manager complexity
- Pay only for what you use

See [infra-appservice/README.md](./infra-appservice/README.md) for cost optimization tips.

## Troubleshooting

Common issues and solutions:

### General Issues
1. **App not accessible**: Check App Service status with `az webapp show --name <webapp> --resource-group <rg>`
2. **Build fails**: Check Dockerfile and dependencies in `pyproject.toml`
3. **Deploy fails**: Verify GitHub Secrets and Azure permissions
4. **Containers not starting**: Check logs with `az webapp log tail --name <webapp> --resource-group <rg>`

### App Service Issues
1. **Backend not responding (502/503)**: Backend container may still be starting (1-2 minutes)
   ```bash
   az webapp log tail --name <webapp> --resource-group <rg>
   ```
2. **Images not pulling**: Verify managed identity has AcrPull role
   ```bash
   az webapp identity show --name <webapp> --resource-group <rg>
   ```
3. **Check container status**:
   ```bash
   az rest --method GET \
     --uri "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/<rg>/providers/Microsoft.Web/sites/<webapp>/sitecontainers?api-version=2024-04-01" \
     --query "value[].{name:name, isMain:properties.isMain, image:properties.image}" \
     --output table
   ```

For detailed troubleshooting guides, see:
- [Azure App Service Deployment Guide](./docs/AZURE_APPSERVICE_DEPLOYMENT.md#monitoring-and-troubleshooting)
- [Infrastructure Documentation](./infra-appservice/README.md)

### Archived AKS Troubleshooting
For issues with the old AKS architecture, see:
- [Archived K8s Documentation](./k8s-archived/README_ARCHIVED.md)
- [Archived Infrastructure](./infra-aks-archived/README_ARCHIVED.md)

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
