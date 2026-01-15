# GitHub Actions Workflow for ACR and AKS Deployment

This document describes the GitHub Actions workflow that has been created to deploy the Python application to Azure Kubernetes Service (AKS) via Azure Container Registry (ACR).

## Overview

The workflow automates the following process:
1. Builds a Docker image of the Python application using `uv` package manager
2. Pushes the image to Azure Container Registry (ACR)
3. Deploys the application to Azure Kubernetes Service (AKS)

## Files Created

### 1. `/app/Dockerfile`
- Uses Python 3.12 slim base image
- Installs `uv` package manager from official container
- Copies `pyproject.toml` and `uv.lock` for dependency management
- Runs `uv sync --frozen --no-dev` to install production dependencies
- Exposes port 5100 for the FastAPI AG-UI server
- Runs `agui_server.py` as the main application

### 2. `.github/workflows/deploy.yml`
A two-job workflow:

**Job 1: build-and-push**
- Checks out code
- Authenticates to Azure using OIDC
- Logs in to Azure Container Registry
- Sets up Docker Buildx for efficient builds
- Builds and pushes Docker image with multiple tags (SHA and latest)
- Uses GitHub Actions cache for faster builds

**Job 2: deploy**
- Depends on build-and-push job
- Authenticates to Azure
- Gets AKS cluster credentials
- Creates/updates Kubernetes secrets for Azure configuration
- Deploys application using Kubernetes manifests
- Waits for deployment rollout
- Retrieves service external IP

### 3. `/k8s/deployment.yaml`
Kubernetes Deployment manifest:
- Deploys 2 replicas for high availability
- Uses image from ACR with dynamic tag substitution
- Configures environment variables from Kubernetes secrets
- Sets resource requests (256Mi memory, 100m CPU) and limits (512Mi memory, 500m CPU)
- Includes liveness and readiness probes on port 5100

### 4. `/k8s/service.yaml`
Kubernetes Service manifest:
- Creates a LoadBalancer service
- Exposes the application on port 80 (external) -> 5100 (internal)
- Routes traffic to pods with label `app: agentic-devops`

### 5. `/k8s/README.md`
Comprehensive documentation including:
- Prerequisites and setup instructions
- Required GitHub Secrets
- Manual deployment commands
- Troubleshooting tips
- Configuration details

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

### Azure Authentication (for OIDC)
- `AZURE_CLIENT_ID`: Service principal client ID
- `AZURE_TENANT_ID`: Azure AD tenant ID
- `AZURE_SUBSCRIPTION_ID`: Azure subscription ID

### Azure Resources
- `ACR_NAME`: Name of your Azure Container Registry
- `AKS_CLUSTER_NAME`: Name of your AKS cluster
- `AKS_RESOURCE_GROUP`: Resource group containing the AKS cluster

### Application Configuration (Optional)
- `AZURE_AI_PROJECT_ENDPOINT`: Azure AI Foundry endpoint
- `AZURE_AI_MODEL_DEPLOYMENT_NAME`: Azure AI model deployment name
- `OPENAI_API_KEY`: OpenAI API key (fallback if Azure AI not configured)

## Workflow Triggers

The workflow runs:
- Automatically on push to `main` branch
- Manually via workflow_dispatch

## Key Features

1. **Security**: Uses Azure OIDC authentication (no stored credentials)
2. **Efficiency**: Docker layer caching via GitHub Actions cache
3. **Traceability**: Images tagged with both git SHA and 'latest'
4. **Reliability**: Health checks and rollout status monitoring
5. **Scalability**: 2 replicas with LoadBalancer for high availability

## Image Tag Strategy

Images are tagged with:
- `<ACR_NAME>.azurecr.io/agentic-devops-starter:<git-sha>` - Specific version
- `<ACR_NAME>.azurecr.io/agentic-devops-starter:latest` - Latest build

The deployment uses the SHA tag for immutability and reproducibility.

## Prerequisites

Before running the workflow:

1. **Create Azure Resources**:
   ```bash
   # Create resource group
   az group create --name <resource-group> --location <location>
   
   # Create ACR
   az acr create --resource-group <resource-group> --name <acr-name> --sku Basic
   
   # Create AKS
   az aks create --resource-group <resource-group> --name <aks-name> --node-count 2 --attach-acr <acr-name>
   ```

2. **Set up OIDC Federation**:
   - Create service principal
   - Configure federated credentials for GitHub Actions
   - Grant necessary permissions (AcrPush, AKS Contributor)

3. **Configure GitHub Secrets**: Add all required secrets in repository settings

## Deployment Flow

```
┌─────────────────┐
│ Push to main    │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│ Build Docker Image      │
│ - uv sync dependencies  │
│ - Copy application code │
└────────┬────────────────┘
         │
         v
┌─────────────────────┐
│ Push to ACR         │
│ - Tag with SHA      │
│ - Tag with 'latest' │
└────────┬────────────┘
         │
         v
┌────────────────────────┐
│ Deploy to AKS          │
│ - Update secrets       │
│ - Apply manifests      │
│ - Wait for rollout     │
└────────┬───────────────┘
         │
         v
┌────────────────────┐
│ Get External IP    │
│ Application Ready  │
└────────────────────┘
```

## Application Details

The deployed application:
- **Port**: Exposed on port 80 externally, runs on 5100 internally
- **Type**: FastAPI server with AG-UI protocol support
- **Framework**: microsoft-agent-framework for conversational AI
- **Health**: Monitored via HTTP GET on `/` endpoint
- **Scaling**: Horizontal scaling via replica count in deployment.yaml

## Next Steps

1. Configure all required GitHub Secrets
2. Ensure Azure resources are created and accessible
3. Push code to `main` branch or manually trigger the workflow
4. Monitor the workflow execution in GitHub Actions tab
5. Once deployed, access the application via the LoadBalancer IP

## Troubleshooting

If the workflow fails:

1. **Authentication errors**: Verify OIDC federation and service principal permissions
2. **Build errors**: Check Dockerfile syntax and dependency installation
3. **Push errors**: Ensure ACR permissions and network connectivity
4. **Deploy errors**: Verify AKS access and kubectl commands
5. **Pod errors**: Check logs with `kubectl logs -l app=agentic-devops`

See `/k8s/README.md` for detailed troubleshooting commands.

## Security Considerations

- Secrets are stored in Kubernetes secrets (base64 encoded)
- Service principal has minimal required permissions
- OIDC authentication eliminates long-lived credentials
- Container images are scanned by ACR (if enabled)
- Network policies can be added for additional security

## Monitoring

Monitor the deployment:
```bash
# Watch pods
kubectl get pods -l app=agentic-devops -w

# View logs
kubectl logs -l app=agentic-devops -f

# Check service
kubectl get service agentic-devops-service

# Describe deployment
kubectl describe deployment agentic-devops-app
```

## Customization

To customize the deployment:

- **Replicas**: Edit `replicas` in `k8s/deployment.yaml`
- **Resources**: Adjust `requests` and `limits` in `k8s/deployment.yaml`
- **Port**: Change `containerPort` and service `targetPort`
- **Environment**: Add more environment variables in deployment spec
- **Service Type**: Change from LoadBalancer to ClusterIP or NodePort

## Support

For issues or questions, refer to:
- `/k8s/README.md` for Kubernetes-specific documentation
- `/app/README.md` for application documentation
- GitHub Actions logs for workflow execution details
