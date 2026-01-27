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
DB_URL="${DB_URL:-}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf "==============================================\n"
printf "S7 Deep Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "TENANT_B: %s, ORG_B: %s\n" "$TENANT_B" "$ORG_B"
printf "RUN_TENANT_PROVISIONING: %s\n" "$RUN_TENANT_PROVISIONING"
printf "==============================================\n"

tenancy_mode="$(
  curl -s "$BASE_URL/api/v1/health" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tenancy_mode",""))'
)"
if [[ -z "$tenancy_mode" ]]; then
  echo "FAIL: Missing tenancy_mode from /health" >&2
  exit 2
fi

if [[ "$tenancy_mode" == "db-per-tenant" || "$tenancy_mode" == "db-per-tenant-org" ]]; then
  if [[ -z "$DB_URL" && -z "${YUANTUS_DATABASE_URL:-}" ]]; then
    echo "FAIL: Multi-tenant mode requires DB_URL or YUANTUS_DATABASE_URL for CLI seeding." >&2
    echo "Hint: export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'" >&2
    exit 2
  fi
  if [[ "$tenancy_mode" == "db-per-tenant-org" && -z "$DB_URL_TEMPLATE" && -z "${YUANTUS_DATABASE_URL_TEMPLATE:-}" ]]; then
    echo "FAIL: db-per-tenant-org requires DB_URL_TEMPLATE or YUANTUS_DATABASE_URL_TEMPLATE." >&2
    echo "Hint: export DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'" >&2
    exit 2
  fi
fi

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
