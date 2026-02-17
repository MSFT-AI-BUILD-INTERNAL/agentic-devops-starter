# Agentic DevOps Starter

MVP for Agentic DevOps Starter - A complete CI/CD solution for deploying Python applications to **Azure App Service**.

## Overview

This repository provides a full-stack DevOps solution for deploying a Python-based conversational AI application to Azure:

- **Application**: FastAPI backend + React frontend (`/app`)
- **Infrastructure**: Terraform code for ACR, App Service, and Log Analytics (`/infra`)
- **CI/CD**: GitHub Actions workflow for automated deployment (`.github/workflows/deploy.yml`)
- **Monitoring**: Azure Log Analytics for comprehensive logging and metrics
- **Security**: Built-in HTTPS with managed SSL/TLS certificates
- **Deployment**: Single container with sidecar pattern (frontend + backend)

## Architecture

```
┌──────────────────────────────────────────┐
│         GitHub Actions CI/CD             │
│  Build → Push to ACR → Deploy           │
└──────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────┐
│   Azure Container Registry (ACR)         │
└──────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────┐
│       Azure App Service (HTTPS)          │
│  ┌────────────────────────────────────┐  │
│  │  Container (port 8080)             │  │
│  │  ┌──────────┐  ┌──────────┐       │  │
│  │  │  nginx   │→ │ Backend  │       │  │
│  │  │(frontend)│  │(FastAPI) │       │  │
│  │  └──────────┘  └──────────┘       │  │
│  │   Managed by supervisor            │  │
│  └────────────────────────────────────┘  │
│  System-Assigned Managed Identity        │
└──────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────┐
│   Azure Log Analytics Workspace          │
└──────────────────────────────────────────┘
```

## Key Features

- ✅ **Infrastructure as Code**: Terraform for reproducible Azure infrastructure
- ✅ **Modern Python**: Uses `uv` for fast, reliable dependency management
- ✅ **Web-Based Chat UI**: React + TypeScript frontend with real-time streaming
- ✅ **Containerization**: Optimized multi-stage Docker build with supervisor
- ✅ **CI/CD Automation**: GitHub Actions for automated build and deployment
- ✅ **Built-in HTTPS**: Automatic SSL/TLS with managed certificates
- ✅ **Secure Authentication**: OIDC-based Azure auth + System-assigned managed identity
- ✅ **Simplified Architecture**: Fully managed PaaS with no cluster overhead
- ✅ **Cost-Effective**: Predictable pricing with App Service Plan
- ✅ **Auto-Scaling**: Built-in App Service scaling capabilities
- ✅ **Monitoring & Logging**: Azure Log Analytics integration

## Quick Start

### 1. Set Up Development Environment

```bash
# Initialize environment (installs uv, Terraform)
./init.sh
source .venv/bin/activate
```

### 2. Provision Azure Infrastructure

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
# IMPORTANT: Change acr_name and app_service_name to globally unique values

terraform init
terraform apply

# Note outputs for GitHub Secrets
terraform output
```

See [`/infra/README.md`](./infra/README.md) for details.

### 3. Configure GitHub Actions

Set up OIDC authentication and configure secrets:

**Required Secrets:**
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `ACR_NAME` (from terraform output)
- `APP_SERVICE_NAME` (from terraform output)
- `RESOURCE_GROUP` (from terraform output)

See [`docs/APPSERVICE_DEPLOYMENT.md`](./docs/APPSERVICE_DEPLOYMENT.md) for setup guide.

### 4. Deploy Application

```bash
git push origin main
```

Access at: `https://<app-service-name>.azurewebsites.net`

## Cost Estimation

Monthly costs (US East):

| Resource | Cost |
|----------|------|
| App Service Plan (P1v3) | ~$100 |
| ACR (Standard) | ~$20 |
| Log Analytics | ~$10-15 |
| **Total** | **~$130-135** |

**Estimated Total**: ~$130-135/month

## Documentation

- **[Infrastructure Setup](./infra/README.md)**: Terraform configuration
- **[Deployment Guide](./docs/APPSERVICE_DEPLOYMENT.md)**: Complete deployment workflow
- **[Backend API Docs](./app/README.md)**: Python application
- **[Frontend Docs](./app/frontend/README.md)**: React interface

## Development

### Backend
```bash
cd app
uv run agui_server.py
# Runs at http://127.0.0.1:5100
```

### Frontend
```bash
cd app/frontend
npm install
npm run dev
# Runs at http://localhost:5173
```

### Test Combined Container
```bash
docker build -f app/Dockerfile.appservice -t test .
docker run -p 8080:8080 test
# Open http://localhost:8080
```

## Troubleshooting

### View Logs
```bash
az webapp log tail --resource-group <rg> --name <app>
```

### Check Health
```bash
curl https://<app-service-name>.azurewebsites.net/health
```

See [APPSERVICE_DEPLOYMENT.md](./docs/APPSERVICE_DEPLOYMENT.md) for detailed troubleshooting.

## Security

- ✅ HTTPS enforced by default
- ✅ Managed Identity (no stored credentials)
- ✅ Private ACR access
- ✅ Security headers configured
- ✅ Role-based access control

## License

See [LICENSE](./LICENSE) file.

## Support

For issues:
- Check documentation
- Review GitHub Actions logs
- Check Azure Portal
- View App Service logs
