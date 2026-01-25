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
│   ├── main.tf            # AKS resource definition with AGIC addon
│   ├── variables.tf       # AKS input variables
│   └── outputs.tf         # AKS outputs
├── app-gateway/            # Azure Application Gateway module
│   ├── main.tf            # Application Gateway and network resources
│   ├── variables.tf       # Application Gateway input variables
│   └── outputs.tf         # Application Gateway outputs
├── key-vault/              # Azure Key Vault module (NEW)
│   ├── main.tf            # Key Vault for SSL certificate management
│   ├── variables.tf       # Key Vault input variables
│   └── outputs.tf         # Key Vault outputs
├── log-analytics/          # Azure Log Analytics module
│   ├── main.tf            # Log Analytics Workspace and Container Insights
│   ├── variables.tf       # Log Analytics input variables
│   └── outputs.tf         # Log Analytics outputs
├── main.tf                # Root configuration orchestrating modules
├── variables.tf           # Root input variables
├── outputs.tf             # Root outputs
└── terraform.tfvars.example  # Example variable values
```

## Architecture

The infrastructure provisions the following resources:

1. **Resource Group**: Container for all Azure resources
2. **Virtual Network**: Isolated network for Application Gateway and AKS
   - Application Gateway Subnet (10.1.0.0/24)
   - AKS Subnet (10.1.1.0/24)
3. **Azure Key Vault**: Secure storage for SSL certificates (NEW)
   - Managed identity integration with Application Gateway
   - Self-signed certificate generation for testing
   - Access policies for secure certificate management
4. **Azure Application Gateway**: L7 load balancer with advanced traffic management
   - Public IP for external access
   - WAF capabilities (optional with WAF_v2 SKU)
   - SSL/TLS termination with Key Vault integration
   - HTTPS listener on port 443
   - HTTP to HTTPS redirect
   - Path-based routing
5. **Application Gateway Ingress Controller (AGIC)**: Manages Application Gateway from Kubernetes
6. **Azure Container Registry (ACR)**: Private container registry for storing Docker images
7. **Azure Kubernetes Service (AKS)**: Managed Kubernetes cluster for running containerized applications
8. **Azure Log Analytics Workspace**: Centralized logging and monitoring solution for AKS
9. **Container Insights**: Azure Monitor solution for collecting logs and metrics from AKS clusters
10. **Role Assignments**: 
    - AKS to pull images from ACR using managed identity
    - AGIC to manage Application Gateway
    - Application Gateway managed identity to access Key Vault certificates

### Key Features

- **Modular Design**: Separate modules for ACR, AKS, Application Gateway, Key Vault, and Log Analytics for reusability
- **Managed Identity**: Uses user-assigned managed identities for secure authentication
- **SSL Certificate Management**: Azure Key Vault securely stores and manages SSL certificates
- **HTTPS Support**: Native HTTPS support with automatic certificate management
- **ACR Integration**: AKS is automatically configured with AcrPull role to pull images from ACR
- **Auto-scaling**: Node pool configured with auto-scaling (1-5 nodes by default)
- **Network Isolation**: Dedicated VNet with separate subnets for Application Gateway and AKS
- **L7 Load Balancing**: Application Gateway provides advanced traffic management capabilities
- **AGIC**: Application Gateway Ingress Controller for seamless Kubernetes integration
- **Centralized Logging**: Log Analytics Workspace collects logs and metrics from AKS
- **Container Insights**: Pre-configured monitoring solution for containerized workloads
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
   
   You can install Terraform automatically by running the project initialization script from the repository root:
   ```bash
   # Run from repository root directory
   ./init.sh
   ```
   
   Alternatively, install Terraform manually:
   ```bash
   # Install Terraform manually
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install terraform
   ```
   
   Verify installation:
   ```bash
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

# Log Analytics Configuration
log_analytics_workspace_name = "log-agentic-devops"
log_analytics_sku            = "PerGB2018"
log_analytics_retention_days = 30

# Application Gateway Configuration
app_gateway_name            = "appgw-agentic-devops"
vnet_name                   = "vnet-agentic-devops"
vnet_address_space          = "10.1.0.0/16"
app_gateway_sku_name        = "Standard_v2"
app_gateway_capacity        = 2

# Key Vault Configuration for SSL Certificates (NEW)
enable_https                         = true                      # Enable HTTPS
key_vault_name                       = "kv-agentic-devops"       # Globally unique
create_self_signed_cert              = true                      # For testing
certificate_subject                  = "agentic-devops.local"
certificate_dns_names                = ["agentic-devops.local", "*.agentic-devops.local"]
```

**Important**: The `acr_name` and `key_vault_name` must be globally unique across all of Azure.

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
| `log_analytics_workspace_name` | Log Analytics Workspace name | `log-agentic-devops` | No |
| `log_analytics_sku` | Log Analytics SKU | `PerGB2018` | No |
| `log_analytics_retention_days` | Log retention period (days) | `30` | No |
| `app_gateway_name` | Application Gateway name | `appgw-agentic-devops` | No |
| `app_gateway_public_ip_name` | Public IP name for App Gateway | `pip-appgw-agentic-devops` | No |
| `vnet_name` | Virtual network name | `vnet-agentic-devops` | No |
| `vnet_address_space` | VNet address space | `10.1.0.0/16` | No |
| `appgw_subnet_prefix` | App Gateway subnet prefix | `10.1.0.0/24` | No |
| `aks_subnet_prefix` | AKS subnet prefix | `10.1.1.0/24` | No |
| `app_gateway_sku_name` | App Gateway SKU name | `Standard_v2` | No |
| `app_gateway_sku_tier` | App Gateway SKU tier | `Standard_v2` | No |
| `app_gateway_capacity` | App Gateway instance count | `2` | No |
| `waf_firewall_mode` | WAF mode (Detection/Prevention) | `Detection` | No |
| `enable_https` | Enable HTTPS with SSL certificate | `true` | No |
| `key_vault_name` | Key Vault name (globally unique) | `kv-agentic-devops` | Yes* |
| `key_vault_sku` | Key Vault SKU (standard/premium) | `standard` | No |
| `create_self_signed_cert` | Create self-signed cert for testing | `true` | No |
| `certificate_name` | Certificate name in Key Vault | `app-gateway-ssl-cert` | No |
| `ssl_certificate_name` | Certificate name in App Gateway | `appgw-ssl-certificate` | No |
| `certificate_subject` | Certificate subject (CN) | `agentic-devops.local` | No |
| `certificate_dns_names` | Certificate SANs | `["agentic-devops.local"]` | No |

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

### Step 2: Apply the Configuration

Deploy the infrastructure:

```bash
terraform apply
```

You'll be prompted to confirm. Type `yes` to proceed.

The deployment typically takes 10-15 minutes. Terraform will create:
1. Resource Group (1-2 minutes)
2. Log Analytics Workspace (2-3 minutes)
3. Container Insights Solution (1-2 minutes)
4. Azure Container Registry (2-3 minutes)
5. Virtual Network and Subnets (1-2 minutes)
6. Application Gateway with Public IP and Managed Identity (3-5 minutes)
7. Azure Key Vault with SSL Certificate (2-3 minutes)
8. Azure Kubernetes Service with AGIC addon (8-12 minutes)
9. Role Assignments and Access Policies (< 1 minute)

**Important Note on HTTPS Setup:**

Due to Terraform resource dependencies, the initial deployment creates the Application Gateway without the SSL certificate. After the first deployment:

1. **Option A: Two-Step Terraform Apply (Recommended)**
   ```bash
   # First apply creates all resources
   terraform apply
   
   # Second apply adds the certificate to Application Gateway
   # (The certificate secret ID is now available from Key Vault)
   terraform apply -refresh-only  # Refresh state
   terraform apply                # Apply certificate configuration
   ```

2. **Option B: Manual Certificate Configuration**
   ```bash
   # After terraform apply, add certificate via Azure Portal:
   # Azure Portal → Application Gateway → Listeners → Add HTTPS listener
   # Select certificate from Key Vault
   ```

The self-signed certificate will be created in Key Vault during the first apply. The Application Gateway can be updated to use it in the second apply or manually via the portal.

### Step 3: Retrieve Outputs

After successful deployment, Terraform displays important outputs:

```bash
# View all outputs
terraform output

# View specific output
terraform output acr_login_server
terraform output app_gateway_public_ip
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

## Azure Log Analytics and Container Insights

The infrastructure includes Azure Log Analytics Workspace with Container Insights, which automatically collects logs and metrics from your AKS cluster.

### What Gets Monitored

Container Insights provides comprehensive monitoring for:

1. **Container Performance**: CPU and memory usage for containers and nodes
2. **Container Logs**: stdout/stderr logs from all containers
3. **Kubernetes Events**: Deployment, pod, and service events
4. **Node Metrics**: Node-level CPU, memory, disk, and network metrics
5. **Cluster Health**: Overall cluster status and health metrics

### Accessing Logs and Metrics

#### Option 1: Azure Portal

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to your AKS cluster resource (e.g., `aks-agentic-devops`)
3. In the left menu, under **Monitoring**, select:
   - **Insights**: Pre-built dashboards showing cluster health, node performance, and container metrics
   - **Logs**: Query logs using Kusto Query Language (KQL)
   - **Workbooks**: Advanced visualization and reporting

#### Option 2: Azure CLI

Query logs directly from the command line:

```bash
# Get the Log Analytics Workspace ID
WORKSPACE_ID=$(terraform output -raw log_analytics_workspace_id)

# Query container logs (last 1 hour)
az monitor log-analytics query \
  --workspace $WORKSPACE_ID \
  --analytics-query "ContainerLog | where TimeGenerated > ago(1h) | limit 100" \
  --output table

# Query performance metrics
az monitor log-analytics query \
  --workspace $WORKSPACE_ID \
  --analytics-query "Perf | where TimeGenerated > ago(1h) | limit 100" \
  --output table
```

### Common Log Analytics Queries

Here are some useful KQL queries you can run in the Azure Portal Logs section:

#### View Container Logs
```kql
ContainerLog
| where TimeGenerated > ago(1h)
| project TimeGenerated, Computer, ContainerID, LogEntry
| order by TimeGenerated desc
| limit 100
```

#### Monitor Container CPU Usage
```kql
Perf
| where ObjectName == "K8SContainer" and CounterName == "cpuUsageNanoCores"
| where TimeGenerated > ago(1h)
| summarize AvgCPU = avg(CounterValue) by bin(TimeGenerated, 5m), InstanceName
| render timechart
```

#### Monitor Container Memory Usage
```kql
Perf
| where ObjectName == "K8SContainer" and CounterName == "memoryRssBytes"
| where TimeGenerated > ago(1h)
| summarize AvgMemory = avg(CounterValue) by bin(TimeGenerated, 5m), InstanceName
| render timechart
```

#### View Kubernetes Events
```kql
KubeEvents
| where TimeGenerated > ago(1h)
| project TimeGenerated, Namespace, Name, Reason, Message
| order by TimeGenerated desc
```

#### Find Error Logs
```kql
ContainerLog
| where TimeGenerated > ago(24h)
| where LogEntry contains "error" or LogEntry contains "Error" or LogEntry contains "ERROR"
| project TimeGenerated, Computer, ContainerID, LogEntry
| order by TimeGenerated desc
```

#### Pod Restart Analysis
```kql
KubePodInventory
| where TimeGenerated > ago(24h)
| where PodStatus == "Failed" or RestartCount > 0
| summarize TotalRestarts = sum(RestartCount) by Name, Namespace
| order by TotalRestarts desc
```

### Setting Up Alerts

Create alerts to be notified of issues:

```bash
# Example: Create alert for high CPU usage
az monitor metrics alert create \
  --name "AKS-High-CPU" \
  --resource-group rg-agentic-devops \
  --scopes $(terraform output -raw aks_id) \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --description "Alert when AKS CPU usage is over 80%"
```

### Log Retention and Costs

- **Default Retention**: 30 days (configurable via `log_analytics_retention_days` variable)
- **Cost**: Pay-per-GB ingestion model (PerGB2018 SKU)
- **Estimated Cost**: Approximately $2-3/GB/month for data ingestion and retention

To optimize costs:
- Adjust retention period based on compliance requirements
- Use data collection rules to filter unnecessary logs
- Archive older logs to Azure Storage for long-term retention

### Troubleshooting Log Analytics

#### Check if Container Insights is enabled:
```bash
# Verify OMS agent is running
kubectl get pods -n kube-system | grep omsagent

# Check OMS agent logs if having issues
kubectl logs -n kube-system -l component=oms-agent --tail=50
```

#### Verify Log Analytics connection:
```bash
# Check addon profile
az aks show \
  --resource-group rg-agentic-devops \
  --name aks-agentic-devops \
  --query "addonProfiles.omsagent" \
  --output table
```

#### Common Issues:

1. **No data appearing in Log Analytics**
   - Wait 5-10 minutes after cluster creation for initial data ingestion
   - Verify OMS agent pods are running: `kubectl get pods -n kube-system | grep omsagent`
   - Check that the workspace ID is correctly configured

2. **High costs**
   - Review data ingestion volume in the Log Analytics Workspace
   - Consider reducing log verbosity for applications
   - Adjust retention period if long-term storage isn't needed

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
az acr show --name $(terraform output -raw acr_name)
```

## Cost Estimation

Approximate monthly costs (US East region):

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| AKS | 2 x Standard_D2s_v3 nodes | ~$140/month |
| AKS Management | Free | $0 |
| ACR | Standard tier | ~$20/month |
| Application Gateway | Standard_v2, 2 instances | ~$140-200/month |
| VNet | Standard | ~$5/month |
| Key Vault | Standard tier | ~$0.03/10k operations |
| SSL Certificate | Self-signed (free) or purchased | $0-50/year |
| Log Analytics | ~5 GB/month data ingestion | ~$10-15/month |
| Container Insights | Included with Log Analytics | $0 |
| **Total** | | **~$315-380/month** |

**Note**: Key Vault costs are minimal (~$0.03 per 10,000 operations). SSL certificates can be free (self-signed) or purchased from a CA.

**Application Gateway Benefits:**
- L7 load balancing with path-based routing
- SSL/TLS termination
- Web Application Firewall (WAF) capabilities (with WAF_v2 SKU)
- Cookie-based session affinity
- Health probing and automatic failover
- Integration with Azure services

To reduce costs:
- Use `Basic` ACR SKU (~$5/month)
- Use smaller VM sizes (e.g., `Standard_B2s`)
- Reduce minimum node count to 1
- Use `Standard_v2` instead of `WAF_v2` for Application Gateway
- Reduce Application Gateway capacity to 1 instance
- Reduce Log Analytics retention period (minimum 7 days)
- Use free tier Log Analytics for development (500 MB/day limit)
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

5. **Log Analytics not receiving data**
   ```
   No data in Container Insights
   ```
   Solution: Wait 5-10 minutes for initial data ingestion, then verify OMS agent is running:
   ```bash
   kubectl get pods -n kube-system | grep omsagent
   kubectl logs -n kube-system -l component=oms-agent --tail=50
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
4. Delete Container Insights solution
5. Delete Log Analytics Workspace
6. Delete resource group

**Warning**: This action is irreversible. All data, including container images, logs, and configurations, will be permanently deleted.

### Selective Cleanup

To remove only specific resources, use targeted destroy:

```bash
# Destroy only AKS
terraform destroy -target=module.aks

# Destroy only ACR
terraform destroy -target=module.acr

# Destroy only Log Analytics
terraform destroy -target=module.log_analytics
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
