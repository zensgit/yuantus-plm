#!/usr/bin/env bash
# =============================================================================
# S7 Deep Verification (Multi-Tenancy + Quota + Audit + Ops + Search + Provision)
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"
TENANT_B="${4:-tenant-2}"
ORG_B="${5:-org-2}"

RUN_TENANT_PROVISIONING="${RUN_TENANT_PROVISIONING:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf "==============================================\n"
printf "S7 Deep Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "TENANT_B: %s, ORG_B: %s\n" "$TENANT_B" "$ORG_B"
printf "RUN_TENANT_PROVISIONING: %s\n" "$RUN_TENANT_PROVISIONING"
printf "==============================================\n"

printf "\n==> Ops Hardening (Multi-Tenancy + Quota + Audit + Ops + Search)\n"
bash "$SCRIPT_DIR/verify_ops_hardening.sh" "$BASE_URL" "$TENANT" "$ORG" "$TENANT_B" "$ORG_B"

if [[ "$RUN_TENANT_PROVISIONING" == "1" ]]; then
  printf "\n==> Tenant Provisioning\n"
  bash "$SCRIPT_DIR/verify_tenant_provisioning.sh" "$BASE_URL" "$TENANT" "$ORG"
else
  printf "\nSKIP: Tenant Provisioning (RUN_TENANT_PROVISIONING=0)\n"
fi

printf "\n==============================================\n"
printf "S7 Deep Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
