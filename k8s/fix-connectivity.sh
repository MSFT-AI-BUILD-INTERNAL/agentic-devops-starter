#!/bin/bash
set -e

#===============================================================================
# Manual Remediation Script for Istio Ingress Gateway Connectivity Issues
# 
# This script fixes the ERR_CONNECTION_TIMED_OUT issue by ensuring proper
# Azure Load Balancer configuration on the istio-ingressgateway service.
#
# Usage: ./fix-connectivity.sh
#===============================================================================

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; exit 1; }
step()  { echo -e "\n${BLUE}=========================================${NC}"; echo -e "${BLUE} $*${NC}"; echo -e "${BLUE}=========================================${NC}"; }

step "Istio Ingress Gateway Connectivity Fix"

# Check prerequisites
if ! kubectl cluster-info &> /dev/null; then
    error "kubectl is not configured. Run: az aks get-credentials --resource-group <RG> --name <AKS>"
fi

# Check if Istio is installed
if ! kubectl get namespace istio-system &> /dev/null; then
    error "Istio is not installed. Run deployment workflow first."
fi

# Check if istio-ingressgateway service exists
if ! kubectl get svc istio-ingressgateway -n istio-system &> /dev/null; then
    error "istio-ingressgateway service not found. Ensure Istio is properly installed."
fi

echo ""
echo "📋 Current Service Configuration:"
kubectl get svc istio-ingressgateway -n istio-system

echo ""
echo "📋 Current Annotations:"
kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.metadata.annotations}' | jq '.' 2>/dev/null || kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.metadata.annotations}'

echo ""
step "Step 1: Applying Azure Load Balancer Annotations"

# Apply external Load Balancer annotation
echo "🔧 Setting azure-load-balancer-internal=false..."
kubectl annotate svc istio-ingressgateway -n istio-system \
  "service.beta.kubernetes.io/azure-load-balancer-internal=false" \
  --overwrite

# Apply health probe configuration
echo "🔧 Configuring health probe path..."
kubectl annotate svc istio-ingressgateway -n istio-system \
  "service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz/ready" \
  --overwrite

info "Annotations applied successfully"

echo ""
step "Step 2: Waiting for Load Balancer Reconfiguration"

echo "⏳ Azure Load Balancer is reconfiguring (this may take 1-3 minutes)..."
echo "   The service will be briefly unavailable during this process."

# Wait for the service to be updated
sleep 5

echo ""
echo "📋 Updated Service Configuration:"
kubectl get svc istio-ingressgateway -n istio-system

echo ""
step "Step 3: Verifying External IP Assignment"

INGRESS_IP=""
for i in {1..30}; do
    INGRESS_IP=$(kubectl get svc istio-ingressgateway -n istio-system \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$INGRESS_IP" ]; then
        break
    fi
    echo "  Attempt ${i}/30: Waiting for External IP..."
    sleep 10
done

if [ -z "$INGRESS_IP" ]; then
    warn "LoadBalancer IP not assigned after 300s."
    echo "   This may indicate an Azure networking issue."
    echo "   Check: kubectl describe svc istio-ingressgateway -n istio-system"
    exit 1
fi

info "External IP assigned: ${INGRESS_IP}"

echo ""
step "Step 4: Testing Connectivity"

echo "🔍 Testing HTTP connectivity to ${INGRESS_IP}..."
sleep 10  # Give Azure Load Balancer time to propagate

# Capture both HTTP code and any error messages
CURL_OUTPUT=$(mktemp)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "http://${INGRESS_IP}" 2>"$CURL_OUTPUT" || echo "000")
CURL_ERROR=$(cat "$CURL_OUTPUT")
rm -f "$CURL_OUTPUT"

if [ "$HTTP_CODE" != "000" ]; then
    info "HTTP response: ${HTTP_CODE}"
    if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
        info "✨ Connectivity test PASSED!"
    else
        warn "Received HTTP ${HTTP_CODE} - service is reachable but may have application issues"
    fi
else
    warn "Connection still timing out after fix."
    if [ -n "$CURL_ERROR" ]; then
        echo "   Error details: $CURL_ERROR"
    fi
    echo ""
    echo "Additional troubleshooting steps:"
    echo "1. Check Azure Network Security Group rules:"
    echo "   - Navigate to Azure Portal → Resource Group → Network Security Groups"
    echo "   - Ensure inbound rules allow ports 80 and 443 from Internet"
    echo ""
    echo "2. Verify Load Balancer health probes:"
    echo "   - Azure Portal → Resource Group → Load Balancers"
    echo "   - Check health probe status (should be healthy)"
    echo ""
    echo "3. Check Istio gateway logs:"
    echo "   kubectl logs -n istio-system -l app=istio-ingressgateway --tail=50"
    echo ""
    echo "4. Wait an additional 2-5 minutes for Azure Load Balancer to fully converge"
fi

echo ""
step "Summary"

echo ""
echo "  🌐 External IP: ${INGRESS_IP}"
echo "  📡 Frontend:    http://${INGRESS_IP}/"
echo "  📡 Backend API: http://${INGRESS_IP}/api"
echo "  📡 Health:      http://${INGRESS_IP}/health"
echo ""
echo "  📝 To verify annotations:"
echo "     kubectl get svc istio-ingressgateway -n istio-system -o yaml | grep azure-load-balancer"
echo ""
echo "  📝 To check Load Balancer status:"
echo "     kubectl describe svc istio-ingressgateway -n istio-system"
echo ""
