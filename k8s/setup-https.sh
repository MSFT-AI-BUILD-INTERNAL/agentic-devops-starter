#!/bin/bash
set -e

echo "🔒 Setting up HTTPS for AKS cluster"

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured. Please run 'az aks get-credentials' first."
    exit 1
fi

# 1. Install NGINX Ingress Controller
echo "📦 Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml

echo "⏳ Waiting for NGINX Ingress Controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

# 2. Install cert-manager
echo "📦 Installing cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

echo "⏳ Waiting for cert-manager to be ready..."
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=300s

# 3. Get NGINX Ingress external IP
echo ""
echo "⏳ Waiting for LoadBalancer IP assignment..."
sleep 30
INGRESS_IP=$(kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

if [ -z "$INGRESS_IP" ]; then
    echo "⚠️  LoadBalancer IP not yet assigned. Please wait and check with:"
    echo "   kubectl get service ingress-nginx-controller -n ingress-nginx"
else
    echo "✅ NGINX Ingress LoadBalancer IP: $INGRESS_IP"
fi

echo ""
echo "📝 Next steps:"
echo "1. Point your domain to the LoadBalancer IP: $INGRESS_IP"
echo "2. Update k8s/ingress.yaml with your domain name"
echo "3. Update k8s/cert-issuer.yaml with your email address"
echo "4. Apply the cert-issuer:"
echo "   kubectl apply -f k8s/cert-issuer.yaml"
echo "5. Apply the ingress:"
echo "   kubectl apply -f k8s/ingress.yaml"
echo ""
echo "✅ Setup complete!"
