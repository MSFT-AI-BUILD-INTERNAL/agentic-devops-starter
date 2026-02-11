#!/bin/bash
set -e

echo "🚀 Installing Istio on AKS cluster"

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured. Please run 'az aks get-credentials' first."
    exit 1
fi

# Set Istio version
ISTIO_VERSION=${ISTIO_VERSION:-1.21.0}
echo "📦 Installing Istio version: $ISTIO_VERSION"

# Download and install istioctl if not already installed
if ! command -v istioctl &> /dev/null; then
    echo "📥 Downloading istioctl..."
    curl -L https://istio.io/downloadIstio | ISTIO_VERSION=$ISTIO_VERSION sh -
    cd istio-$ISTIO_VERSION
    export PATH=$PWD/bin:$PATH
    cd ..
else
    echo "✅ istioctl already installed"
fi

# Install Istio with minimal profile and enable ingress gateway
echo "📦 Installing Istio components..."
istioctl install --set profile=default \
  --set components.ingressGateways[0].enabled=true \
  --set components.ingressGateways[0].name=istio-ingressgateway \
  --set components.ingressGateways[0].k8s.service.type=LoadBalancer \
  --set components.ingressGateways[0].k8s.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-internal"="false" \
  --set meshConfig.accessLogFile=/dev/stdout \
  -y

# Wait for Istio components to be ready
echo "⏳ Waiting for Istio components to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/istiod -n istio-system
kubectl wait --for=condition=available --timeout=300s deployment/istio-ingressgateway -n istio-system

# Get the LoadBalancer IP
echo ""
echo "⏳ Waiting for LoadBalancer IP assignment..."
sleep 15

INGRESS_IP=""
for i in {1..12}; do
    INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$INGRESS_IP" ]; then
        break
    fi
    echo "  Attempt $i/12: Waiting for IP..."
    sleep 10
done

if [ -z "$INGRESS_IP" ]; then
    echo "⚠️  LoadBalancer IP not yet assigned. Please check with:"
    echo "   kubectl get service istio-ingressgateway -n istio-system"
else
    echo "✅ Istio Ingress Gateway LoadBalancer IP: $INGRESS_IP"
fi

echo ""
echo "✅ Istio installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Apply Gateway and VirtualService manifests:"
echo "   kubectl apply -f k8s/istio-gateway.yaml"
echo "   kubectl apply -f k8s/istio-virtualservice.yaml"
echo "2. For HTTPS with Let's Encrypt:"
echo "   - Install cert-manager: kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml"
echo "   - Set LETSENCRYPT_EMAIL: export LETSENCRYPT_EMAIL=your-email@example.com"
echo "   - Apply cert-issuer: envsubst < k8s/cert-issuer-istio.yaml | kubectl apply -f -"
echo "   - Apply certificate: envsubst < k8s/istio-certificate.yaml | kubectl apply -f -"
echo "3. Access your application at: http://$INGRESS_IP"
