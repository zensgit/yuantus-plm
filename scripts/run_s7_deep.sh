#!/usr/bin/env bash
# =============================================================================
# Run S7 deep verification with sane defaults for docker-compose.mt.yml
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"
TENANT_B="${4:-tenant-2}"
ORG_B="${5:-org-2}"

MODE_DEFAULT="db-per-tenant-org"
DB_URL_DEFAULT="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus"
DB_URL_TEMPLATE_DEFAULT="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
IDENTITY_DB_URL_DEFAULT="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg"

MODE="${MODE:-${YUANTUS_TENANCY_MODE:-$MODE_DEFAULT}}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-$DB_URL_DEFAULT}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-$DB_URL_TEMPLATE_DEFAULT}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-$IDENTITY_DB_URL_DEFAULT}}"
RUN_TENANT_PROVISIONING="${RUN_TENANT_PROVISIONING:-1}"

health_json="$(curl -s "$BASE_URL/api/v1/health" || true)"
tenancy_mode="$(printf '%s' "$health_json" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tenancy_mode",""))')"
if [[ -z "$tenancy_mode" ]]; then
  echo "FAIL: API health check failed or tenancy_mode missing" >&2
  echo "Hint: ensure API is running and reachable at $BASE_URL" >&2
  exit 2
fi

if [[ "$tenancy_mode" != "db-per-tenant" && "$tenancy_mode" != "db-per-tenant-org" ]]; then
  echo "FAIL: tenancy_mode=$tenancy_mode (expected db-per-tenant or db-per-tenant-org)" >&2
  echo "Hint: start with docker compose -f docker-compose.yml -f docker-compose.mt.yml up -d" >&2
  exit 2
fi

export MODE DB_URL DB_URL_TEMPLATE IDENTITY_DB_URL RUN_TENANT_PROVISIONING

printf "==============================================\n"
printf "S7 Deep Verification Runner\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "TENANT_B: %s, ORG_B: %s\n" "$TENANT_B" "$ORG_B"
printf "MODE: %s\n" "$MODE"
printf "DB_URL: %s\n" "$DB_URL"
printf "DB_URL_TEMPLATE: %s\n" "$DB_URL_TEMPLATE"
printf "IDENTITY_DB_URL: %s\n" "$IDENTITY_DB_URL"
printf "RUN_TENANT_PROVISIONING: %s\n" "$RUN_TENANT_PROVISIONING"
printf "==============================================\n\n"

bash scripts/verify_s7.sh "$BASE_URL" "$TENANT" "$ORG" "$TENANT_B" "$ORG_B"
