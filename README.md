# Agentic DevOps Starter

MVP for Agentic DevOps Starter (Compass) - A complete CI/CD solution for deploying Python applications to Azure Kubernetes Service.

## Overview

This repository provides a full-stack DevOps solution for deploying a Python-based conversational AI application to Azure:

- **Application**: FastAPI server with AG-UI protocol support (`/app`)
- **Infrastructure**: Terraform code for ACR and AKS (`/infra`)
- **CI/CD**: GitHub Actions workflow for automated deployment (`.github/workflows/deploy.yml`)
- **Kubernetes**: Manifests for container orchestration (`/k8s`)

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

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```yaml
# From Terraform outputs
ACR_NAME: <output from terraform>
AKS_CLUSTER_NAME: <output from terraform>
AKS_RESOURCE_GROUP: <output from terraform>

# Azure Authentication (OIDC)
AZURE_CLIENT_ID: <your-service-principal-client-id>
AZURE_TENANT_ID: <your-tenant-id>
AZURE_SUBSCRIPTION_ID: <your-subscription-id>

# Application Configuration (Optional)
AZURE_AI_PROJECT_ENDPOINT: <your-azure-ai-endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME: <your-model-deployment>
OPENAI_API_KEY: <your-openai-key>
```

### 4. Deploy Application

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
```

## Key Features

- ✅ **Infrastructure as Code**: Terraform for reproducible Azure infrastructure
- ✅ **Modern Python**: Uses `uv` for fast, reliable dependency management
- ✅ **Web-Based Chat UI**: React + TypeScript frontend with real-time streaming (NEW)
- ✅ **Containerization**: Optimized Docker images with multi-stage builds
- ✅ **CI/CD Automation**: GitHub Actions for automated build and deployment
- ✅ **Kubernetes Orchestration**: High-availability deployment with health checks
- ✅ **Secure Authentication**: OIDC-based Azure authentication (no stored credentials)
- ✅ **Comprehensive Docs**: Detailed guides for infrastructure, deployment, and operations

## Documentation

- **[Infrastructure Setup](./infra/README.md)**: Terraform configuration and Azure resources
- **[Deployment Guide](./DEPLOYMENT.md)**: Complete deployment workflow and troubleshooting
- **[Kubernetes Config](./k8s/README.md)**: Kubernetes manifests and operations
- **[Backend API Docs](./app/README.md)**: Python application architecture and usage
- **[Frontend Chatbot UI](./frontend/README.md)**: Web interface setup and development (NEW)
- **[Feature Specification](./specs/003-copilotkit-frontend/spec.md)**: Chatbot frontend requirements
- **[Quickstart Guide](./specs/003-copilotkit-frontend/quickstart.md)**: 5-minute setup for chat UI

## Development

### Running Locally with Frontend

The application now includes a web-based chatbot interface for interacting with the AI agent.

#### Backend Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Configure environment variables
cd app
cp .env.example .env
# Edit .env with your Azure OpenAI or OpenAI API keys

# Run the backend server
python agui_server.py
```

The backend server will start at `http://127.0.0.1:5100`

#### Frontend Setup (in a new terminal)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

**Quick Test**: Open http://localhost:5173 in your browser and start chatting with the AI assistant!

### Frontend Development

```bash
cd frontend

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

For detailed frontend documentation, see [`/frontend/README.md`](./frontend/README.md).

### Backend Development

```bash
cd app

# Run with auto-reload (development)
python -m uvicorn agui_server:get_app --reload --host 127.0.0.1 --port 5100 --factory

# Run tests
pytest tests/

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
- **Total**: ~$180/month

See [infra/README.md](./infra/README.md) for cost optimization tips.

## Troubleshooting

Common issues and solutions:

1. **Build fails**: Check Dockerfile and dependencies in `pyproject.toml`
2. **Deploy fails**: Verify GitHub Secrets and Azure permissions
3. **Pods not starting**: Check logs with `kubectl logs -l app=agentic-devops`
4. **Can't access service**: Wait for LoadBalancer IP assignment

For detailed troubleshooting, see:
- [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting)
- [infra/README.md](./infra/README.md#troubleshooting)
- [k8s/README.md](./k8s/README.md#troubleshooting)

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
