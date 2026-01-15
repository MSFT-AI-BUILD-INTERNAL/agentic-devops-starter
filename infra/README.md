# Azure Infrastructure with Terraform

This directory contains Terraform Infrastructure as Code (IaC) for deploying Azure Container Registry (ACR) and Azure Kubernetes Service (AKS) for the Agentic DevOps Starter project.

## Overview

The infrastructure is organized into modular components:

```
infra/
├── acr/                    # Azure Container Registry module
│   ├── main.tf            # ACR resource definition
│   ├── variables.tf       # ACR input variables
│   └── outputs.tf         # ACR outputs
├── aks/                    # Azure Kubernetes Service module
│   ├── main.tf            # AKS resource definition
│   ├── variables.tf       # AKS input variables
│   └── outputs.tf         # AKS outputs
├── main.tf                # Root configuration orchestrating modules
├── variables.tf           # Root input variables
├── outputs.tf             # Root outputs
└── terraform.tfvars.example  # Example variable values
```

## Architecture

The infrastructure provisions the following resources:

1. **Resource Group**: Container for all Azure resources
2. **Azure Container Registry (ACR)**: Private container registry for storing Docker images
3. **Azure Kubernetes Service (AKS)**: Managed Kubernetes cluster for running containerized applications
4. **Role Assignment**: Configures AKS to pull images from ACR using managed identity

### Key Features

- **Modular Design**: Separate modules for ACR and AKS for reusability
- **Managed Identity**: Uses system-assigned managed identities for secure authentication
- **ACR Integration**: AKS is automatically configured with AcrPull role to pull images from ACR
- **Auto-scaling**: Node pool configured with auto-scaling (1-5 nodes by default)
- **Network Configuration**: Uses Azure CNI for advanced networking capabilities
- **Tagging**: Comprehensive tagging for resource organization and cost tracking

## Prerequisites

Before deploying this infrastructure, ensure you have:

1. **Azure CLI** (version 2.50.0 or later)
   ```bash
   # Install Azure CLI
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   
   # Verify installation
   az --version
   ```

2. **Terraform** (version 1.5.0 or later)
   ```bash
   # Install Terraform
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install terraform
   
   # Verify installation
   terraform --version
   ```

3. **Azure Subscription** with appropriate permissions to create:
   - Resource Groups
   - Container Registries
   - Kubernetes Clusters
   - Role Assignments

4. **kubectl** (optional, for managing the Kubernetes cluster)
   ```bash
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
   
   # Verify installation
   kubectl version --client
   ```

## Configuration

### Step 1: Authenticate with Azure

```bash
# Login to Azure
az login

# Set your subscription (if you have multiple)
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify the current subscription
az account show
```

### Step 2: Configure Variables

Create a `terraform.tfvars` file from the example:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` to customize your deployment:

```hcl
# Resource Group Configuration
resource_group_name = "rg-agentic-devops"
location            = "eastus"  # Change to your preferred region

# Azure Container Registry Configuration
acr_name         = "acragenticdevops123"  # MUST be globally unique!
acr_sku          = "Standard"
acr_admin_enabled = false

# Azure Kubernetes Service Configuration
aks_cluster_name   = "aks-agentic-devops"
aks_dns_prefix     = "aks-agentic-devops"
kubernetes_version = "1.28"

# Node Pool Configuration
node_count          = 2
vm_size             = "Standard_D2s_v3"
enable_auto_scaling = true
min_node_count      = 1
max_node_count      = 5
```

**Important**: The `acr_name` must be globally unique across all of Azure and contain only alphanumeric characters.

### Step 3: Review Available Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `resource_group_name` | Name of the resource group | `rg-agentic-devops` | No |
| `location` | Azure region | `eastus` | No |
| `acr_name` | ACR name (globally unique) | `acragenticdevops` | Yes* |
| `acr_sku` | ACR tier (Basic/Standard/Premium) | `Standard` | No |
| `acr_admin_enabled` | Enable ACR admin user | `false` | No |
| `aks_cluster_name` | AKS cluster name | `aks-agentic-devops` | No |
| `aks_dns_prefix` | DNS prefix for AKS | `aks-agentic-devops` | No |
| `kubernetes_version` | Kubernetes version | `1.28` | No |
| `node_count` | Initial node count | `2` | No |
| `vm_size` | VM size for nodes | `Standard_D2s_v3` | No |
| `enable_auto_scaling` | Enable auto-scaling | `true` | No |
| `min_node_count` | Min nodes (auto-scaling) | `1` | No |
| `max_node_count` | Max nodes (auto-scaling) | `5` | No |

\* Must be customized to ensure global uniqueness

## Deployment

### Step 1: Initialize Terraform

Navigate to the `infra` directory and initialize Terraform:

```bash
cd infra
terraform init
```

This will:
- Download the required Azure provider plugins
- Initialize the backend
- Set up the working directory

### Step 2: Plan the Deployment

Review the changes that will be made:

```bash
terraform plan
```

This command shows you:
- Resources that will be created
- Configuration details
- Any potential issues

### Step 3: Apply the Configuration

Deploy the infrastructure:

```bash
terraform apply
```

You'll be prompted to confirm. Type `yes` to proceed.

The deployment typically takes 10-15 minutes. Terraform will create:
1. Resource Group (1-2 minutes)
2. Azure Container Registry (2-3 minutes)
3. Azure Kubernetes Service (8-12 minutes)
4. Role Assignment (< 1 minute)

### Step 4: Retrieve Outputs

After successful deployment, Terraform displays important outputs:

```bash
# View all outputs
terraform output

# View specific output
terraform output acr_login_server
terraform output configure_kubectl_command
```

## Post-Deployment Configuration

### Configure kubectl Access

Connect to your AKS cluster:

```bash
# Get credentials (use the command from Terraform output)
az aks get-credentials --resource-group rg-agentic-devops --name aks-agentic-devops

# Verify connection
kubectl get nodes
kubectl cluster-info
```

### Test ACR Access

Verify ACR is accessible:

```bash
# Get ACR login server
ACR_NAME=$(terraform output -raw acr_name)
ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)

# Login to ACR
az acr login --name $ACR_NAME

# List repositories (should be empty initially)
az acr repository list --name $(terraform output -raw acr_name)
```

### Push a Test Image to ACR

```bash
# Pull a test image
docker pull nginx:latest

# Tag for your ACR
docker tag nginx:latest ${ACR_LOGIN_SERVER}/nginx:v1

# Push to ACR
docker push ${ACR_LOGIN_SERVER}/nginx:v1

# Verify
az acr repository list --name $ACR_NAME
az acr repository show-tags --name $ACR_NAME --repository nginx
```

### Deploy a Test Application to AKS

Create a test deployment that pulls from ACR:

```bash
# Create a deployment YAML
cat <<EOF > test-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-test
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: ${ACR_LOGIN_SERVER}/nginx:v1
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-test
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: nginx
EOF

# Deploy to AKS
kubectl apply -f test-deployment.yaml

# Check status
kubectl get deployments
kubectl get pods
kubectl get services

# Get external IP (may take a few minutes)
kubectl get service nginx-test -w
```

## GitHub Actions Integration

To integrate with GitHub Actions for CI/CD:

### 1. Set Up Azure Service Principal

```bash
# Create service principal with contributor access
az ad sp create-for-rbac --name "github-actions-agentic-devops" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/rg-agentic-devops \
  --sdk-auth

# Save the output JSON - you'll need it for GitHub Secrets
```

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository:

- `AZURE_CREDENTIALS`: The full JSON output from the service principal creation
- `AZURE_SUBSCRIPTION_ID`: Your Azure subscription ID
- `ACR_LOGIN_SERVER`: Output from `terraform output acr_login_server`
- `ACR_NAME`: Output from `terraform output acr_name`
- `AKS_CLUSTER_NAME`: Output from `terraform output aks_name`
- `AKS_RESOURCE_GROUP`: Output from `terraform output resource_group_name`

### 3. Example GitHub Actions Workflow

Update `.github/workflows/deploy.yml` to use the infrastructure:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Build and push image to ACR
      run: |
        az acr build --registry ${{ secrets.ACR_NAME }} \
          --image myapp:${{ github.sha }} \
          --file ./app/Dockerfile ./app
    
    - name: Set up kubeconfig
      run: |
        az aks get-credentials \
          --resource-group ${{ secrets.AKS_RESOURCE_GROUP }} \
          --name ${{ secrets.AKS_CLUSTER_NAME }}
    
    - name: Deploy to AKS
      run: |
        kubectl set image deployment/myapp \
          myapp=${{ secrets.ACR_LOGIN_SERVER }}/myapp:${{ github.sha }}
```

## Maintenance

### Updating Infrastructure

To modify the infrastructure:

1. Update variables in `terraform.tfvars` or module configurations
2. Run `terraform plan` to preview changes
3. Run `terraform apply` to apply changes

### Scaling the Cluster

To manually scale the node pool:

```bash
# Using Azure CLI
az aks scale --resource-group rg-agentic-devops \
  --name aks-agentic-devops \
  --node-count 3

# Or update terraform.tfvars and re-apply
```

### Upgrading Kubernetes

```bash
# Check available versions
az aks get-upgrades --resource-group rg-agentic-devops \
  --name aks-agentic-devops

# Update kubernetes_version in terraform.tfvars
# Then apply
terraform apply
```

### Viewing Logs

```bash
# AKS logs
az aks show --resource-group rg-agentic-devops \
  --name aks-agentic-devops

# ACR logs
az acr show --name acragenticdevops
```

## Cost Estimation

Approximate monthly costs (US East region):

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| AKS | 2 x Standard_D2s_v3 nodes | ~$140/month |
| AKS Management | Free | $0 |
| ACR | Standard tier | ~$20/month |
| Load Balancer | Standard | ~$20/month |
| **Total** | | **~$180/month** |

To reduce costs:
- Use `Basic` ACR SKU (~$5/month)
- Use smaller VM sizes (e.g., `Standard_B2s`)
- Reduce minimum node count to 1
- Delete resources when not in use

## Troubleshooting

### Common Issues

1. **ACR name already taken**
   ```
   Error: creating Container Registry: name already in use
   ```
   Solution: Change `acr_name` to a globally unique value in `terraform.tfvars`

2. **Insufficient quota**
   ```
   Error: creating Kubernetes Cluster: quota exceeded
   ```
   Solution: Request quota increase in Azure Portal or choose different region/VM size

3. **kubectl connection issues**
   ```
   Unable to connect to the server
   ```
   Solution: Re-run `az aks get-credentials` and verify `kubectl config current-context`

4. **AKS can't pull from ACR**
   ```
   ImagePullBackOff error
   ```
   Solution: Verify role assignment exists:
   ```bash
   az role assignment list --scope $(terraform output -raw acr_id)
   ```

### Debug Mode

Enable Terraform debug logging:

```bash
export TF_LOG=DEBUG
terraform apply
```

### Getting Help

- Check Terraform state: `terraform show`
- View resource details: `az resource show --ids <resource-id>`
- Review activity logs: Azure Portal → Monitor → Activity Log

## Clean Up

### Destroy Infrastructure

To remove all resources:

```bash
# Preview what will be destroyed
terraform plan -destroy

# Destroy all resources
terraform destroy
```

Type `yes` when prompted. This will:
1. Remove role assignments
2. Delete AKS cluster (5-10 minutes)
3. Delete ACR
4. Delete resource group

**Warning**: This action is irreversible. All data, including container images and configurations, will be permanently deleted.

### Selective Cleanup

To remove only specific resources, use targeted destroy:

```bash
# Destroy only AKS
terraform destroy -target=module.aks

# Destroy only ACR
terraform destroy -target=module.acr
```

### Verify Cleanup

```bash
# Check if resource group is deleted
az group show --name rg-agentic-devops

# Should return: ResourceGroupNotFound
```

## Security Best Practices

1. **Use Managed Identities**: Already configured - avoid using admin credentials
2. **Private Endpoints**: For production, consider using private endpoints for ACR
3. **Network Policies**: Configured with Azure Network Policy
4. **RBAC**: Use Azure RBAC for access control
5. **Secrets Management**: Use Azure Key Vault for sensitive data
6. **Regular Updates**: Keep Kubernetes version up to date

## Additional Resources

- [Azure Container Registry Documentation](https://docs.microsoft.com/azure/container-registry/)
- [Azure Kubernetes Service Documentation](https://docs.microsoft.com/azure/aks/)
- [Terraform Azure Provider Documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## Contributing

When making changes to the infrastructure:

1. Test changes in a development environment first
2. Update this README if adding new features
3. Follow Terraform best practices
4. Document any new variables or outputs

## License

See LICENSE file in the repository root.
