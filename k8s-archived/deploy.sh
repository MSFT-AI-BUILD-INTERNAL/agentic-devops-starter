#!/bin/bash
set -e

#===============================================================================
# Istio Ingress Gateway Full Deployment Script
# - Istio 설치 → 앱 배포 → Gateway/VirtualService → 연결 검증
#===============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISTIO_VERSION="${ISTIO_VERSION:-1.24.3}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; exit 1; }
step()  { echo -e "\n${GREEN}=========================================${NC}"; echo -e "${GREEN} $*${NC}"; echo -e "${GREEN}=========================================${NC}"; }

#===============================================================================
# Step 0: Prerequisites
#===============================================================================
step "Step 0: Checking prerequisites"

if ! kubectl cluster-info &> /dev/null; then
    error "kubectl is not configured. Run: az aks get-credentials --resource-group <RG> --name <AKS>"
fi
info "kubectl connected to cluster"

kubectl version --client --short 2>/dev/null || true
echo "Server: $(kubectl version -o json 2>/dev/null | grep -o '"gitVersion":"[^"]*"' | head -1)"

#===============================================================================
# Step 1: Install Istio
#===============================================================================
step "Step 1: Installing Istio ${ISTIO_VERSION}"

# Download istioctl if not on PATH
if ! command -v istioctl &> /dev/null; then
    if [ -d "${SCRIPT_DIR}/istio-${ISTIO_VERSION}" ]; then
        info "Istio ${ISTIO_VERSION} already downloaded"
    else
        echo "📥 Downloading istioctl ${ISTIO_VERSION}..."
        cd "${SCRIPT_DIR}"
        curl -sL https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
    fi
    export PATH="${SCRIPT_DIR}/istio-${ISTIO_VERSION}/bin:${PATH}"
fi

if ! command -v istioctl &> /dev/null; then
    error "istioctl not found on PATH after installation"
fi
info "istioctl version: $(istioctl version --remote=false 2>/dev/null)"

# Install Istio control plane + ingress gateway
echo "📦 Installing Istio components..."
istioctl install --set profile=default \
  --set components.ingressGateways[0].enabled=true \
  --set components.ingressGateways[0].name=istio-ingressgateway \
  --set meshConfig.accessLogFile=/dev/stdout \
  -y

# Wait for Istio pods
echo "⏳ Waiting for Istio pods..."
kubectl wait --for=condition=available --timeout=300s deployment/istiod -n istio-system
kubectl wait --for=condition=available --timeout=300s deployment/istio-ingressgateway -n istio-system
info "Istio pods are ready"

# Annotate for external (public) Azure Load Balancer
kubectl annotate svc istio-ingressgateway -n istio-system \
  "service.beta.kubernetes.io/azure-load-balancer-internal=false" \
  --overwrite
info "Ingress gateway annotated for external LB"

#===============================================================================
# Step 2: Wait for External IP
#===============================================================================
step "Step 2: Waiting for LoadBalancer External IP"

INGRESS_IP=""
for i in {1..20}; do
    INGRESS_IP=$(kubectl get svc istio-ingressgateway -n istio-system \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$INGRESS_IP" ]; then
        break
    fi
    echo "  Attempt ${i}/20: Waiting for IP..."
    sleep 10
done

if [ -z "$INGRESS_IP" ]; then
    error "LoadBalancer IP not assigned after 200s. Check: kubectl get svc -n istio-system"
fi
info "External IP: ${INGRESS_IP}"

#===============================================================================
# Step 3: Enable Istio sidecar injection for default namespace
#===============================================================================
step "Step 3: Enabling Istio sidecar injection"

kubectl label namespace default istio-injection=enabled --overwrite
info "Sidecar injection enabled for 'default' namespace"

#===============================================================================
# Step 4: Deploy application (Service Account → Service → Deployment)
#===============================================================================
step "Step 4: Deploying application"

# Service Account
echo "📦 Applying ServiceAccount..."
if [ -n "${AZURE_CLIENT_ID}" ]; then
    envsubst < "${SCRIPT_DIR}/service-account.yaml" | kubectl apply -f -
else
    warn "AZURE_CLIENT_ID not set — applying ServiceAccount without workload identity"
    sed 's/\${AZURE_CLIENT_ID}/placeholder/g' "${SCRIPT_DIR}/service-account.yaml" | kubectl apply -f -
fi

# Service (ClusterIP — routed via Istio Ingress Gateway)
echo "📦 Applying Service..."
kubectl apply -f "${SCRIPT_DIR}/service.yaml"

# Deployment
echo "📦 Applying Deployment..."
ACR_NAME="${ACR_NAME:-acragenticdevops}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
export ACR_NAME IMAGE_TAG
envsubst < "${SCRIPT_DIR}/deployment.yaml" | kubectl apply -f -

echo "⏳ Waiting for deployment rollout..."
kubectl rollout status deployment/agentic-devops-app --timeout=300s
info "Application deployed"

#===============================================================================
# Step 5: Apply Istio Gateway & VirtualService
#===============================================================================
step "Step 5: Applying Istio Gateway & VirtualService"

kubectl apply -f "${SCRIPT_DIR}/istio-gateway.yaml"
kubectl apply -f "${SCRIPT_DIR}/istio-virtualservice.yaml"
info "Gateway and VirtualService applied"

#===============================================================================
# Step 6: Restart pods for sidecar injection (if needed)
#===============================================================================
step "Step 6: Ensuring sidecar injection"

# Check if pods have istio-proxy sidecar
SIDECAR_COUNT=$(kubectl get pods -l app=agentic-devops -o jsonpath='{range .items[*]}{.spec.containers[*].name}{"\n"}{end}' 2>/dev/null | grep -c "istio-proxy" || echo "0")

if [ "$SIDECAR_COUNT" -eq 0 ]; then
    warn "Pods don't have Istio sidecar. Restarting deployment..."
    kubectl rollout restart deployment/agentic-devops-app
    kubectl rollout status deployment/agentic-devops-app --timeout=300s
    info "Pods restarted with sidecar injection"
else
    info "Pods already have Istio sidecar (${SIDECAR_COUNT} found)"
fi

#===============================================================================
# Step 7: Verify connectivity
#===============================================================================
step "Step 7: Verifying connectivity"

echo ""
echo "📋 Istio System:"
kubectl get pods -n istio-system
echo ""
echo "📋 Application:"
kubectl get pods -l app=agentic-devops
echo ""
echo "📋 Services:"
kubectl get svc istio-ingressgateway -n istio-system
echo ""
echo "📋 Gateway & VirtualService:"
kubectl get gateway,virtualservice -A
echo ""

# Test connectivity
echo "🔍 Testing HTTP connectivity to ${INGRESS_IP}..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "http://${INGRESS_IP}" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" != "000" ]; then
    info "HTTP response: ${HTTP_CODE}"
else
    warn "Connection timed out — LB health probes may still be converging. Retry in ~30s."
fi

#===============================================================================
# Summary
#===============================================================================
step "Deployment Complete!"

echo ""
echo "  🌐 External IP: ${INGRESS_IP}"
echo "  📡 Frontend:    http://${INGRESS_IP}/"
echo "  📡 Backend API: http://${INGRESS_IP}/api"
echo "  📡 Health:      http://${INGRESS_IP}/health"
echo ""
echo "  📝 For HTTPS setup, run:"
echo "     export LETSENCRYPT_EMAIL=your-email@example.com"
echo "     ${SCRIPT_DIR}/setup-istio-https.sh"
echo ""
