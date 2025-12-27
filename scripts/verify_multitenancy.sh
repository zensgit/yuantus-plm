#!/usr/bin/env bash
# =============================================================================
# S7 Multi-Tenancy Verification Script
# Verifies tenant/org isolation for db-per-tenant or db-per-tenant-org modes.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT_A="${2:-tenant-1}"
TENANT_B="${3:-tenant-2}"
ORG_A="${4:-org-1}"
ORG_B="${5:-org-2}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

MODE="${MODE:-}"
DB_URL="${DB_URL:-}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

API="$BASE_URL/api/v1"

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$MODE" || -n "$DB_URL" || -n "$DB_URL_TEMPLATE" || -n "$identity_url" ]]; then
    env \
      ${MODE:+YUANTUS_TENANCY_MODE="$MODE"} \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

login() {
  local tenant="$1"
  local org="$2"
  local username="$3"
  local password="$4"
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$tenant\",\"username\":\"$username\",\"password\":\"$password\",\"org_id\":\"$org\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
}

aml_add() {
  local tenant="$1"
  local org="$2"
  local token="$3"
  local item_number="$4"
  local name="$5"

  local payload
  payload="$(printf '{"type":"Part","action":"add","properties":{"item_number":"%s","name":"%s"}}' "$item_number" "$name")"
  $CURL -X POST "$API/aml/apply" \
    -H "Authorization: Bearer $token" \
    -H "x-tenant-id: $tenant" -H "x-org-id: $org" \
    -H 'content-type: application/json' \
    -d "$payload" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
}

aml_count() {
  local tenant="$1"
  local org="$2"
  local token="$3"
  local item_number="$4"

  local payload
  payload="$(printf '{"type":"Part","action":"get","properties":{"item_number":"%s"}}' "$item_number")"
  $CURL -X POST "$API/aml/apply" \
    -H "Authorization: Bearer $token" \
    -H "x-tenant-id: $tenant" -H "x-org-id: $org" \
    -H 'content-type: application/json' \
    -d "$payload" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("count",0))'
}

echo "=============================================="
echo "Multi-Tenancy Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT_A: $TENANT_A, TENANT_B: $TENANT_B"
echo "ORG_A: $ORG_A, ORG_B: $ORG_B"
echo "=============================================="

if [[ -z "$MODE" ]]; then
  MODE="$(
    $CURL "$API/health" \
      | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("tenancy_mode",""))'
  )"
fi

if [[ -z "$MODE" ]]; then
  fail "Missing tenancy_mode from /health; upgrade API to include tenancy_mode"
fi

if [[ "$MODE" != "db-per-tenant" && "$MODE" != "db-per-tenant-org" ]]; then
  echo "SKIP: tenancy_mode=$MODE (set YUANTUS_TENANCY_MODE=db-per-tenant|db-per-tenant-org)"
  exit 0
fi

TS="$(date +%s)"
USER_ID_BASE=$((TS % 2000000000))
USER_ID_A="$USER_ID_BASE"
USER_ID_B=$((USER_ID_BASE + 1))

if [[ "$MODE" == "db-per-tenant" ]]; then
  echo ""
  echo "==> Seed identity/meta for two tenants"
  USER_A="admin-${TENANT_A}-${TS}"
  USER_B="admin-${TENANT_B}-${TS}"
  run_cli seed-identity --tenant "$TENANT_A" --org "$ORG_A" --username "$USER_A" --password admin --user-id "$USER_ID_A" --roles admin --superuser >/dev/null
  run_cli seed-identity --tenant "$TENANT_B" --org "$ORG_A" --username "$USER_B" --password admin --user-id "$USER_ID_B" --roles admin --superuser >/dev/null
  run_cli seed-meta --tenant "$TENANT_A" >/dev/null
  run_cli seed-meta --tenant "$TENANT_B" >/dev/null
  ok "Seeded tenants"

  echo ""
  echo "==> Login for each tenant"
  TOKEN_A="$(login "$TENANT_A" "$ORG_A" "$USER_A" "admin")"
  TOKEN_B="$(login "$TENANT_B" "$ORG_A" "$USER_B" "admin")"
  if [[ -z "$TOKEN_A" || -z "$TOKEN_B" ]]; then
    fail "Login failed for one or more tenants"
  fi
  ok "Login succeeded"

  echo ""
  echo "==> Create Part in tenant A and verify isolation"
  ITEM_A="MT-T1-$TS"
  PART_A="$(aml_add "$TENANT_A" "$ORG_A" "$TOKEN_A" "$ITEM_A" "Tenant A Part")"
  [[ -z "$PART_A" ]] && fail "Failed to create Part in tenant A"
  COUNT_A="$(aml_count "$TENANT_A" "$ORG_A" "$TOKEN_A" "$ITEM_A")"
  COUNT_B="$(aml_count "$TENANT_B" "$ORG_A" "$TOKEN_B" "$ITEM_A")"
  [[ "$COUNT_A" -eq 1 ]] || fail "Tenant A should see item (count=$COUNT_A)"
  [[ "$COUNT_B" -eq 0 ]] || fail "Tenant B should not see tenant A item (count=$COUNT_B)"
  ok "Tenant isolation A -> B"

  echo ""
  echo "==> Create Part in tenant B and verify isolation"
  ITEM_B="MT-T2-$TS"
  PART_B="$(aml_add "$TENANT_B" "$ORG_A" "$TOKEN_B" "$ITEM_B" "Tenant B Part")"
  [[ -z "$PART_B" ]] && fail "Failed to create Part in tenant B"
  COUNT_A="$(aml_count "$TENANT_A" "$ORG_A" "$TOKEN_A" "$ITEM_B")"
  COUNT_B="$(aml_count "$TENANT_B" "$ORG_A" "$TOKEN_B" "$ITEM_B")"
  [[ "$COUNT_B" -eq 1 ]] || fail "Tenant B should see item (count=$COUNT_B)"
  [[ "$COUNT_A" -eq 0 ]] || fail "Tenant A should not see tenant B item (count=$COUNT_A)"
  ok "Tenant isolation B -> A"
else
  echo ""
  echo "==> Seed identity/meta for tenant/org combos"
  USER_A="admin-${TENANT_A}-${TS}"
  USER_B="admin-${TENANT_B}-${TS}"
  run_cli seed-identity --tenant "$TENANT_A" --org "$ORG_A" --username "$USER_A" --password admin --user-id "$USER_ID_A" --roles admin --superuser >/dev/null
  run_cli seed-identity --tenant "$TENANT_A" --org "$ORG_B" --username "$USER_A" --password admin --user-id "$USER_ID_A" --roles admin --superuser >/dev/null
  run_cli seed-identity --tenant "$TENANT_B" --org "$ORG_A" --username "$USER_B" --password admin --user-id "$USER_ID_B" --roles admin --superuser >/dev/null

  run_cli seed-meta --tenant "$TENANT_A" --org "$ORG_A" >/dev/null
  run_cli seed-meta --tenant "$TENANT_A" --org "$ORG_B" >/dev/null
  run_cli seed-meta --tenant "$TENANT_B" --org "$ORG_A" >/dev/null
  ok "Seeded tenant/org schemas"

  echo ""
  echo "==> Login for each tenant/org"
  TOKEN_A1="$(login "$TENANT_A" "$ORG_A" "$USER_A" "admin")"
  TOKEN_A2="$(login "$TENANT_A" "$ORG_B" "$USER_A" "admin")"
  TOKEN_B1="$(login "$TENANT_B" "$ORG_A" "$USER_B" "admin")"
  if [[ -z "$TOKEN_A1" || -z "$TOKEN_A2" || -z "$TOKEN_B1" ]]; then
    fail "Login failed for one or more tenant/org contexts"
  fi
  ok "Login succeeded"

  echo ""
  echo "==> Create Part in tenant A/org A and verify isolation"
  ITEM_A1="MT-A1-$TS"
  PART_A1="$(aml_add "$TENANT_A" "$ORG_A" "$TOKEN_A1" "$ITEM_A1" "Tenant A Org A Part")"
  [[ -z "$PART_A1" ]] && fail "Failed to create Part in tenant A/org A"
  COUNT_A1="$(aml_count "$TENANT_A" "$ORG_A" "$TOKEN_A1" "$ITEM_A1")"
  COUNT_A2="$(aml_count "$TENANT_A" "$ORG_B" "$TOKEN_A2" "$ITEM_A1")"
  COUNT_B1="$(aml_count "$TENANT_B" "$ORG_A" "$TOKEN_B1" "$ITEM_A1")"
  [[ "$COUNT_A1" -eq 1 ]] || fail "Org A should see item (count=$COUNT_A1)"
  [[ "$COUNT_A2" -eq 0 ]] || fail "Org B should not see org A item (count=$COUNT_A2)"
  [[ "$COUNT_B1" -eq 0 ]] || fail "Tenant B should not see tenant A item (count=$COUNT_B1)"
  ok "Org + tenant isolation (A1)"

  echo ""
  echo "==> Create Part in tenant A/org B and verify isolation"
  ITEM_A2="MT-A2-$TS"
  PART_A2="$(aml_add "$TENANT_A" "$ORG_B" "$TOKEN_A2" "$ITEM_A2" "Tenant A Org B Part")"
  [[ -z "$PART_A2" ]] && fail "Failed to create Part in tenant A/org B"
  COUNT_A1="$(aml_count "$TENANT_A" "$ORG_A" "$TOKEN_A1" "$ITEM_A2")"
  COUNT_A2="$(aml_count "$TENANT_A" "$ORG_B" "$TOKEN_A2" "$ITEM_A2")"
  [[ "$COUNT_A2" -eq 1 ]] || fail "Org B should see item (count=$COUNT_A2)"
  [[ "$COUNT_A1" -eq 0 ]] || fail "Org A should not see org B item (count=$COUNT_A1)"
  ok "Org isolation (A2)"

  echo ""
  echo "==> Create Part in tenant B/org A and verify isolation"
  ITEM_B1="MT-B1-$TS"
  PART_B1="$(aml_add "$TENANT_B" "$ORG_A" "$TOKEN_B1" "$ITEM_B1" "Tenant B Org A Part")"
  [[ -z "$PART_B1" ]] && fail "Failed to create Part in tenant B/org A"
  COUNT_A1="$(aml_count "$TENANT_A" "$ORG_A" "$TOKEN_A1" "$ITEM_B1")"
  COUNT_B1="$(aml_count "$TENANT_B" "$ORG_A" "$TOKEN_B1" "$ITEM_B1")"
  [[ "$COUNT_B1" -eq 1 ]] || fail "Tenant B should see item (count=$COUNT_B1)"
  [[ "$COUNT_A1" -eq 0 ]] || fail "Tenant A should not see tenant B item (count=$COUNT_A1)"
  ok "Tenant isolation (B1)"
fi

echo ""
echo "=============================================="
echo "Multi-Tenancy Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
