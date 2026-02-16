# Connectivity Issue Fix Summary

## Issue #80 - ERR_CONNECTION_TIMED_OUT

### Problem
Customers experience connection timeout when trying to access the application at http://20.249.160.90 after PR #79 was merged.

### Root Cause
1. **PR #79**: Added Istio sidecar traffic exclusion annotations for Azure Workload Identity
2. **PR #81**: Fixed the Azure Load Balancer annotation placement to run on every deployment
3. **Missing Health Probe Configuration**: Azure Load Balancer health probes were not properly configured for Istio's health check endpoint

When Azure Load Balancer doesn't have proper health probe configuration, it may:
- Mark backend pools as unhealthy
- Not route traffic properly
- Timeout external connections

### Solution
Added comprehensive fix with multiple layers:

1. **Health Probe Annotation** (Primary Fix)
   - Added `service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz/ready`
   - This tells Azure Load Balancer to use Istio's built-in health check endpoint
   - Applied in both `deploy.yml` workflow and `deploy.sh` script

2. **Manual Remediation Script** (`k8s/fix-connectivity.sh`)
   - Automated script to fix connectivity issues without redeployment
   - Applies all necessary annotations
   - Validates connectivity
   - Provides detailed diagnostics

3. **Enhanced Documentation**
   - Updated `README.md` with quick fix instructions
   - Enhanced `docs/ISTIO_SETUP.md` with comprehensive troubleshooting
   - Added troubleshooting section to `k8s/README.md`

4. **Verification Steps**
   - Added annotation verification to the deployment workflow
   - Improved logging and diagnostics

## Files Changed

### Configuration Files
- `.github/workflows/deploy.yml`: Added health probe annotation and verification
- `k8s/deploy.sh`: Added health probe annotation

### New Files
- `k8s/fix-connectivity.sh`: Manual remediation script (executable)

### Documentation
- `README.md`: Updated with quick fix steps
- `docs/ISTIO_SETUP.md`: Comprehensive troubleshooting guide
- `k8s/README.md`: Added connectivity troubleshooting section

## How to Apply the Fix

### Option 1: Automated (Recommended for Immediate Fix)
If the infrastructure is already deployed and having connectivity issues:

```bash
# Run the automated fix script
./k8s/fix-connectivity.sh
```

This will:
1. Apply all necessary annotations
2. Wait for Azure Load Balancer to reconfigure (1-3 minutes)
3. Verify connectivity
4. Provide diagnostics if issues persist

### Option 2: Redeploy via CI/CD
If deploying fresh or via CI/CD:

```bash
# The GitHub Actions workflow will automatically apply all annotations
# Simply push to main or manually trigger the workflow
```

The updated workflow ensures:
- Azure Load Balancer is configured as external (public)
- Health probes use the correct Istio endpoint
- Configuration is verified after deployment

### Option 3: Manual Fix
Apply annotations manually:

```bash
# Set Load Balancer to external
kubectl annotate svc istio-ingressgateway -n istio-system \
  "service.beta.kubernetes.io/azure-load-balancer-internal=false" \
  --overwrite

# Configure health probe path
kubectl annotate svc istio-ingressgateway -n istio-system \
  "service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz/ready" \
  --overwrite

# Wait 2-3 minutes for Azure to reconfigure
# Then verify connectivity
INGRESS_IP=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -v http://$INGRESS_IP
```

## Verification

After applying the fix, verify:

1. **Annotations are present:**
   ```bash
   kubectl get svc istio-ingressgateway -n istio-system -o yaml | grep azure-load-balancer
   ```

   Should show:
   ```
   service.beta.kubernetes.io/azure-load-balancer-internal: "false"
   service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path: /healthz/ready
   ```

2. **External IP is assigned:**
   ```bash
   kubectl get svc istio-ingressgateway -n istio-system
   ```

   Should show an EXTERNAL-IP (not `<pending>`)

3. **Connectivity works:**
   ```bash
   curl -v http://<EXTERNAL-IP>
   ```

   Should return HTTP response (not timeout)

4. **Health probes are healthy (Azure Portal):**
   - Navigate to: Resource Groups → AKS RG → Load Balancers
   - Check backend pool health status
   - Should show "Healthy"

## Additional Considerations

### Azure Load Balancer Reconfiguration Time
- After applying annotations, Azure needs 1-3 minutes to reconfigure
- Service may be briefly unavailable during reconfiguration
- Health probes need time to stabilize

### Network Security Groups
If connectivity still fails after applying the fix:
1. Check NSG inbound rules allow ports 80 and 443
2. Verify rules apply to the correct subnet
3. Check for any deny rules that override allow rules

### Istio Health Check Endpoint
Istio ingress gateway provides health check at:
- Path: `/healthz/ready`
- Port: 15021 (status port)
- Protocol: HTTP

Azure Load Balancer is configured to probe this endpoint to determine backend health.

## References

- Issue #80: https://github.com/MSFT-AI-BUILD-INTERNAL/agentic-devops-starter/issues/80
- PR #79: https://github.com/MSFT-AI-BUILD-INTERNAL/agentic-devops-starter/pull/79
- PR #81: https://github.com/MSFT-AI-BUILD-INTERNAL/agentic-devops-starter/pull/81
- Azure Load Balancer Health Probes: https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-custom-probe-overview
- Istio Gateway: https://istio.io/latest/docs/reference/config/networking/gateway/
