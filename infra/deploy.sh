#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Terraform deploy with automatic import of existing Azure resources
#
# Usage:
#   ./deploy.sh              # import + plan + apply (interactive)
#   ./deploy.sh --plan-only  # import + plan (no apply)
#   ./deploy.sh --auto       # import + plan + apply -auto-approve
#
# Prerequisites:
#   - az CLI logged in (`az login`)
#   - terraform >= 1.5
#   - terraform.tfvars configured
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Flags ───────────────────────────────────────────────────────────────────
PLAN_ONLY=false
AUTO_APPROVE=false
for arg in "$@"; do
  case "$arg" in
    --plan-only) PLAN_ONLY=true ;;
    --auto)      AUTO_APPROVE=true ;;
    -h|--help)
      echo "Usage: $0 [--plan-only] [--auto]"
      echo "  --plan-only  Run import + plan only, do not apply"
      echo "  --auto       Apply with -auto-approve (no prompt)"
      exit 0
      ;;
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

# ── Cleanup on exit ────────────────────────────────────────────────────────
cleanup() { rm -f tfplan; }
trap cleanup EXIT

# ── Helpers ─────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m▶ $*\033[0m"; }
ok()    { echo -e "\033[1;32m✔ $*\033[0m"; }
warn()  { echo -e "\033[1;33m⚠ $*\033[0m"; }
err()   { echo -e "\033[1;31m✘ $*\033[0m"; }

# Cached state list (populated once after terraform init)
STATE_LIST=""
refresh_state_list() {
  STATE_LIST=$(terraform state list 2>/dev/null || true)
}

in_state() {
  echo "$STATE_LIST" | grep -qF "$1"
}

# Try to import a resource; skip if already in state or not found in Azure
try_import() {
  local tf_addr="$1"
  local azure_id="$2"

  if in_state "$tf_addr"; then
    ok "Already in state: $tf_addr"
    return 0
  fi

  if [ -z "$azure_id" ]; then
    warn "Skipping $tf_addr — resource not found in Azure"
    return 0
  fi

  info "Importing $tf_addr"
  if terraform import "$tf_addr" "$azure_id" 2>&1; then
    ok "Imported: $tf_addr"
  else
    warn "Import failed for $tf_addr (will be created by apply)"
  fi
}

# ── Load variables from terraform.tfvars ────────────────────────────────────
if [ ! -f terraform.tfvars ]; then
  err "terraform.tfvars not found. Copy terraform.tfvars.example and configure it."
  exit 1
fi

get_var() {
  local line value
  line=$(awk -v key="$1" -F= '$1 ~ "^[[:space:]]*" key "[[:space:]]*$" { print; exit }' terraform.tfvars)
  value="${line#*=}"
  value="${value%%#*}"
  value="${value//\"/}"
  echo "$value" | xargs
}

RG_NAME=$(get_var resource_group_name)
LOCATION=$(get_var location)
ACR_NAME=$(get_var acr_name)
ASP_NAME=$(get_var app_service_plan_name)
APP_NAME=$(get_var app_service_name)
LOG_NAME=$(get_var log_analytics_workspace_name)
VNET_NAME=$(get_var vnet_name)
STORAGE_NAME=$(get_var storage_account_name)
UPLOADS_CONTAINER=$(get_var uploads_container_name)
AZURE_AI_PROJECT_ENDPOINT=$(get_var azure_ai_project_endpoint)
AZURE_AI_MODEL_DEPLOYMENT_NAME=$(get_var azure_ai_model_deployment_name)
AZURE_OPENAI_API_VERSION=$(get_var azure_openai_api_version)
AI_FOUNDRY_RESOURCE_ID=$(get_var ai_foundry_resource_id)

SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

info "Subscription: $SUB_ID"
info "Resource Group: $RG_NAME"

# ── Terraform init ──────────────────────────────────────────────────────────
info "Running terraform init"
terraform init -input=false

# Cache current state for idempotent import checks
refresh_state_list

# ── Discover existing Azure resources ───────────────────────────────────────
info "Checking for existing Azure resources..."

resolve_id() {
  az resource show --ids "$1" --query id -o tsv 2>/dev/null || echo ""
}

resolve_role_assignment_id() {
  local principal_id="$1"
  local scope="$2"
  local role_name="$3"

  if [ -z "$principal_id" ] || [ -z "$scope" ]; then
    echo ""
    return 0
  fi

  az role assignment list \
    --assignee "$principal_id" \
    --scope "$scope" \
    --role "$role_name" \
    --query "[0].id" -o tsv 2>/dev/null || echo ""
}

RG_ID=$(az group show --name "$RG_NAME" --query id -o tsv 2>/dev/null || echo "")

if [ -n "$RG_ID" ]; then
  ok "Found resource group: $RG_NAME"

  LOG_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.OperationalInsights/workspaces/$LOG_NAME")
  VNET_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.Network/virtualNetworks/$VNET_NAME")
  ACR_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME")
  ASP_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.Web/serverFarms/$ASP_NAME")
  APP_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.Web/sites/$APP_NAME")
  APP_PRINCIPAL_ID=$(az webapp identity show --resource-group "$RG_NAME" --name "$APP_NAME" --query principalId -o tsv 2>/dev/null || echo "")
  STORAGE_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME")

  # Subnets
  APP_SUBNET_ID=$(az network vnet subnet show --resource-group "$RG_NAME" --vnet-name "$VNET_NAME" --name "snet-app-integration" --query id -o tsv 2>/dev/null || echo "")
  PE_SUBNET_ID=$(az network vnet subnet show --resource-group "$RG_NAME" --vnet-name "$VNET_NAME" --name "snet-private-endpoints" --query id -o tsv 2>/dev/null || echo "")

  # Private DNS zone
  DNS_ZONE_ID=$(az network private-dns zone show --resource-group "$RG_NAME" --name "privatelink.blob.core.windows.net" --query id -o tsv 2>/dev/null || echo "")

  # Private DNS VNet link
  DNS_LINK_ID=$(az network private-dns link vnet show --resource-group "$RG_NAME" --zone-name "privatelink.blob.core.windows.net" --name "${VNET_NAME}-blob-dns-link" --query id -o tsv 2>/dev/null || echo "")

  # Private endpoint
  PE_NAME="pe-${STORAGE_NAME}-blob"
  PE_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.Network/privateEndpoints/$PE_NAME")

  # Log Analytics solution (Container Insights)
  LOG_SOLUTION_ID=""
  if [ -n "$LOG_ID" ]; then
    LOG_SOLUTION_ID=$(resolve_id "/subscriptions/$SUB_ID/resourceGroups/$RG_NAME/providers/Microsoft.OperationsManagement/solutions/ContainerInsights(${LOG_NAME})")
  fi

  ACR_PULL_ROLE_ID=$(resolve_role_assignment_id "$APP_PRINCIPAL_ID" "$ACR_ID" "AcrPull")
  AI_DEVELOPER_ROLE_ID=$(resolve_role_assignment_id "$APP_PRINCIPAL_ID" "$AI_FOUNDRY_RESOURCE_ID" "Azure AI Developer")
  COGNITIVE_SERVICES_USER_ROLE_ID=$(resolve_role_assignment_id "$APP_PRINCIPAL_ID" "$AI_FOUNDRY_RESOURCE_ID" "Cognitive Services User")
else
  warn "Resource group '$RG_NAME' not found — all resources will be created"
  LOG_ID="" VNET_ID="" ACR_ID="" ASP_ID="" APP_ID="" STORAGE_ID=""
  APP_PRINCIPAL_ID=""
  APP_SUBNET_ID="" PE_SUBNET_ID="" DNS_ZONE_ID="" DNS_LINK_ID="" PE_ID=""
  LOG_SOLUTION_ID=""
  ACR_PULL_ROLE_ID="" AI_DEVELOPER_ROLE_ID="" COGNITIVE_SERVICES_USER_ROLE_ID=""
fi

# ── Import existing resources ───────────────────────────────────────────────
info "Importing existing resources into Terraform state..."

try_import "azurerm_resource_group.main"                           "$RG_ID"
try_import "module.log_analytics.azurerm_log_analytics_workspace.aks" "$LOG_ID"
try_import "module.log_analytics.azurerm_log_analytics_solution.container_insights" "$LOG_SOLUTION_ID"
try_import "module.network.azurerm_virtual_network.main"           "$VNET_ID"
try_import "module.network.azurerm_subnet.app_integration"         "$APP_SUBNET_ID"
try_import "module.network.azurerm_subnet.private_endpoints"       "$PE_SUBNET_ID"
try_import "module.acr.azurerm_container_registry.acr"             "$ACR_ID"
try_import "module.app_service_plan.azurerm_service_plan.main"     "$ASP_ID"
try_import "module.storage.azurerm_storage_account.main"           "$STORAGE_ID"
try_import "module.app_service.azurerm_linux_web_app.main"         "$APP_ID"
try_import "module.app_service.azurerm_role_assignment.acr_pull"   "$ACR_PULL_ROLE_ID"
try_import "module.app_service.azurerm_role_assignment.ai_developer[0]" "$AI_DEVELOPER_ROLE_ID"
try_import "module.app_service.azurerm_role_assignment.cognitive_services_user[0]" "$COGNITIVE_SERVICES_USER_ROLE_ID"
try_import "azurerm_private_dns_zone.blob"                         "$DNS_ZONE_ID"
try_import "azurerm_private_dns_zone_virtual_network_link.blob"    "$DNS_LINK_ID"
try_import "azurerm_private_endpoint.blob"                         "$PE_ID"

# Remove storage container from state if present (no longer managed by Terraform)
if in_state 'module.storage.azurerm_storage_container.containers'; then
  warn "Removing storage container from Terraform state (now managed by deploy script)"
  terraform state rm 'module.storage.azurerm_storage_container.containers["'"${UPLOADS_CONTAINER}"'"]' 2>/dev/null || true
  refresh_state_list
fi

ensure_app_configuration() {
  if ! az webapp show --resource-group "$RG_NAME" --name "$APP_NAME" --query id -o tsv 2>/dev/null 1>/dev/null; then
    warn "App Service '$APP_NAME' not found yet; skipping app settings"
    return 0
  fi

  local blob_endpoint
  blob_endpoint=$(az storage account show \
    --resource-group "$RG_NAME" \
    --name "$STORAGE_NAME" \
    --query "primaryEndpoints.blob" -o tsv 2>/dev/null || echo "")

  get_app_setting() {
    az webapp config appsettings list \
      --resource-group "$RG_NAME" --name "$APP_NAME" \
      --query "[?name=='$1'].value | [0]" -o tsv 2>/dev/null || true
  }

  if [ -z "$blob_endpoint" ]; then
    warn "Storage account '$STORAGE_NAME' not found yet; skipping storage app settings"
  else
    local settings_to_update=()
    local desired_settings=(
      "AZURE_TENANT_ID=$TENANT_ID"
      "AZURE_AI_PROJECT_ENDPOINT=$AZURE_AI_PROJECT_ENDPOINT"
      "AZURE_AI_MODEL_DEPLOYMENT_NAME=$AZURE_AI_MODEL_DEPLOYMENT_NAME"
      "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION"
      "COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT=$blob_endpoint"
      "COPILOT_API_AZURE_STORAGE_CONTAINER_NAME=$UPLOADS_CONTAINER"
    )

    for setting in "${desired_settings[@]}"; do
      local key="${setting%%=*}"
      local desired="${setting#*=}"
      local current
      current=$(get_app_setting "$key")
      if [ "$current" != "$desired" ]; then
        settings_to_update+=("$setting")
      fi
    done

    if [ "${#settings_to_update[@]}" -gt 0 ]; then
      info "Updating changed non-secret App Service settings..."
      az webapp config appsettings set \
        --resource-group "$RG_NAME" \
        --name "$APP_NAME" \
        --settings "${settings_to_update[@]}" \
        --only-show-errors 1>/dev/null
      ok "App Service non-secret settings are ready"
    else
      ok "App Service non-secret settings already match"
    fi
  fi

  if [ -n "${COPILOT_GITHUB_TOKEN:-}" ]; then
    local current_token
    current_token=$(get_app_setting "GITHUB_TOKEN")
    if [ "$current_token" != "$COPILOT_GITHUB_TOKEN" ]; then
      info "Setting GITHUB_TOKEN from COPILOT_GITHUB_TOKEN environment variable..."
      az webapp config appsettings set \
        --resource-group "$RG_NAME" \
        --name "$APP_NAME" \
        --settings GITHUB_TOKEN="$COPILOT_GITHUB_TOKEN" \
        --only-show-errors 1>/dev/null
      ok "GITHUB_TOKEN is ready"
    else
      ok "GITHUB_TOKEN already matches"
    fi
  else
    local current_token
    current_token=$(get_app_setting "GITHUB_TOKEN")

    if [ -z "$current_token" ]; then
      warn "GITHUB_TOKEN is not set. Export COPILOT_GITHUB_TOKEN before running this script, re-run deploy.yml, or set it manually."
    else
      ok "GITHUB_TOKEN is present"
    fi
  fi
}

ensure_blob_container() {
  if ! az storage account show --resource-group "$RG_NAME" --name "$STORAGE_NAME" --query id -o tsv 2>/dev/null 1>/dev/null; then
    warn "Storage account '$STORAGE_NAME' not found yet; skipping blob container"
    return 0
  fi

  info "Ensuring blob container '${UPLOADS_CONTAINER}' exists..."
  local container_id="/subscriptions/${SUB_ID}/resourceGroups/${RG_NAME}/providers/Microsoft.Storage/storageAccounts/${STORAGE_NAME}/blobServices/default/containers/${UPLOADS_CONTAINER}"
  if az resource show --ids "$container_id" --api-version "2023-01-01" --query id -o tsv 2>/dev/null 1>/dev/null; then
    ok "Blob container '${UPLOADS_CONTAINER}' already exists"
  elif az resource create \
      --ids "$container_id" \
      --api-version "2023-01-01" \
      --properties '{"publicAccess":"None"}' \
      --only-show-errors 1>/dev/null; then
    ok "Blob container '${UPLOADS_CONTAINER}' is ready"
  else
    warn "Could not create/verify blob container '${UPLOADS_CONTAINER}' via ARM"
  fi
}

ensure_post_deploy_configuration() {
  ensure_app_configuration
  ensure_blob_container
}

# ── Plan ────────────────────────────────────────────────────────────────────
info "Running terraform plan"
terraform plan -out=tfplan -detailed-exitcode 2>&1 && PLAN_EXIT=0 || PLAN_EXIT=$?
# exit 0 = no changes, exit 1 = error, exit 2 = changes present

if [ "$PLAN_EXIT" -eq 1 ]; then
  err "Terraform plan failed"
  exit 1
fi

if [ "$PLAN_EXIT" -eq 0 ]; then
  ok "No changes needed — infrastructure is up to date"
  ensure_post_deploy_configuration
  exit 0
fi

# Check for destroy actions and warn
DESTROY_OUTPUT=$(terraform show -json tfplan 2>/dev/null \
  | python3 -c "
import sys, json
plan = json.load(sys.stdin)
changes = plan.get('resource_changes', [])
destroys = [c['address'] for c in changes if 'delete' in c.get('change',{}).get('actions',[])]
for d in destroys: print(d)
" 2>/dev/null || true)

if [ -n "$DESTROY_OUTPUT" ]; then
  echo ""
  err "⚠️  WARNING: Plan includes DESTROY actions:"
  echo "$DESTROY_OUTPUT"
  echo ""
  warn "Resources above will be DELETED (and possibly recreated)."
  warn "This may cause downtime or data loss."
  echo ""

  if ! $AUTO_APPROVE; then
    read -rp "Continue despite destroy actions? (yes/N): " confirm
    if [ "$confirm" != "yes" ]; then
      warn "Aborted. Run with --plan-only to review safely."
      exit 1
    fi
  fi
fi

if $PLAN_ONLY; then
  ok "Plan complete. Review above and run: terraform apply tfplan"
  trap - EXIT  # keep tfplan file for manual apply
  exit 0
fi

# ── Apply ───────────────────────────────────────────────────────────────────
if $AUTO_APPROVE; then
  info "Applying changes (auto-approve)"
  terraform apply tfplan
else
  echo ""
  read -rp "Apply these changes? (y/N): " confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    terraform apply tfplan
  else
    warn "Apply cancelled"
    exit 0
  fi
fi

ok "Deployment complete!"
terraform output

# ── Post-apply: settings and resources Terraform intentionally ignores ──────
ensure_post_deploy_configuration
