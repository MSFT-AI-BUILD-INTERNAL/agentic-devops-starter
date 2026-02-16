#!/bin/bash
set -e

echo "🔒 Setting up Istio Ingress Gateway with HTTPS for AKS cluster"

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured. Please run 'az aks get-credentials' first."
    exit 1
fi

# Check if LETSENCRYPT_EMAIL is set
if [ -z "$LETSENCRYPT_EMAIL" ]; then
    echo "⚠️  LETSENCRYPT_EMAIL environment variable is not set."
    echo "   For Let's Encrypt certificate issuance, you need to provide an email address."
    read -p "   Enter your email for Let's Encrypt notifications (or press Enter to skip HTTPS setup): " LETSENCRYPT_EMAIL
    export LETSENCRYPT_EMAIL
fi

# Step 1: Install Istio (handled by deploy.sh)
echo ""
echo "========================================="
echo "Step 1: Installing Istio"
echo "========================================="
./k8s/deploy.sh

# Step 2: Install cert-manager (if not already installed)
echo ""
echo "========================================="
echo "Step 2: Installing cert-manager"
echo "========================================="
if ! kubectl get namespace cert-manager &> /dev/null; then
    echo "📦 Installing cert-manager..."
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml
    
    echo "⏳ Waiting for cert-manager to be ready..."
    kubectl wait --namespace cert-manager \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/instance=cert-manager \
      --timeout=300s
    
    echo "✅ cert-manager installed successfully"
else
    echo "✅ cert-manager already installed, skipping..."
fi

# Step 3: Apply Istio Gateway and VirtualService
echo ""
echo "========================================="
echo "Step 3: Applying Istio Gateway and VirtualService"
echo "========================================="
kubectl apply -f k8s/istio-gateway.yaml
kubectl apply -f k8s/istio-virtualservice.yaml
echo "✅ Istio Gateway and VirtualService applied"

# Step 4: Set up Let's Encrypt (if email is provided)
if [ -n "$LETSENCRYPT_EMAIL" ]; then
    echo ""
    echo "========================================="
    echo "Step 4: Setting up Let's Encrypt"
    echo "========================================="
    
    # Get Istio Ingress Gateway IP
    echo "⏳ Getting Istio Ingress Gateway IP..."
    sleep 5
    INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    if [ -z "$INGRESS_IP" ]; then
        echo "⚠️  LoadBalancer IP not yet assigned. Waiting..."
        for i in {1..12}; do
            sleep 10
            INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
            if [ -n "$INGRESS_IP" ]; then
                break
            fi
            echo "  Attempt $i/12: Waiting for IP..."
        done
    fi
    
    if [ -z "$INGRESS_IP" ]; then
        echo "❌ Failed to get LoadBalancer IP. Please check:"
        echo "   kubectl get service istio-ingressgateway -n istio-system"
        exit 1
    fi
    
    echo "✅ Istio Ingress Gateway IP: $INGRESS_IP"
    
    # Set domain name (use nip.io for testing or custom domain)
    if [ -z "$DOMAIN_NAME" ]; then
        DOMAIN_NAME="${INGRESS_IP}.nip.io"
        echo "ℹ️  Using nip.io domain: $DOMAIN_NAME"
    else
        echo "ℹ️  Using custom domain: $DOMAIN_NAME"
        echo "⚠️  Make sure $DOMAIN_NAME points to $INGRESS_IP in your DNS"
    fi
    export DOMAIN_NAME
    
    # Apply cert-issuer
    echo "📝 Applying Let's Encrypt ClusterIssuer..."
    envsubst < k8s/cert-issuer-istio.yaml | kubectl apply -f -
    
    # Apply certificate
    echo "📝 Applying Certificate resource..."
    envsubst < k8s/istio-certificate.yaml | kubectl apply -f -
    
    echo ""
    echo "⏳ Waiting for certificate to be issued (this may take a few minutes)..."
    echo "   You can check the status with: kubectl describe certificate agentic-devops-tls -n istio-system"
    
    # Wait for certificate to be ready
    sleep 10
    for i in {1..30}; do
        CERT_STATUS=$(kubectl get certificate agentic-devops-tls -n istio-system -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
        if [ "$CERT_STATUS" = "True" ]; then
            echo "✅ Certificate issued successfully!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "⚠️  Certificate issuance is taking longer than expected."
            echo "   Check status: kubectl describe certificate agentic-devops-tls -n istio-system"
            echo "   Check cert-manager logs: kubectl logs -n cert-manager -l app=cert-manager"
            break
        fi
        echo "  Attempt $i/30: Certificate not ready yet..."
        sleep 10
    done
    
    echo ""
    echo "✅ HTTPS setup complete!"
    echo ""
    echo "📝 Access your application at:"
    echo "   HTTP:  http://$DOMAIN_NAME"
    echo "   HTTPS: https://$DOMAIN_NAME"
    echo ""
    echo "💡 To enable HTTP to HTTPS redirect, uncomment the httpsRedirect section in k8s/istio-gateway.yaml"
else
    echo ""
    echo "⚠️  Skipping HTTPS setup (no email provided)"
    echo ""
    INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    echo "📝 Access your application at:"
    echo "   HTTP: http://$INGRESS_IP"
    echo ""
    echo "💡 To set up HTTPS later, run this script again with LETSENCRYPT_EMAIL set:"
    echo "   export LETSENCRYPT_EMAIL=your-email@example.com"
    echo "   ./k8s/setup-istio-https.sh"
fi

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
