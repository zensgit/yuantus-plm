#!/usr/bin/env bash
# =============================================================================
# CAD Capabilities Verification
# Verifies: /api/v1/cad/capabilities payload shape and counts.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

TENANCY_MODE="${TENANCY_MODE:-${YUANTUS_TENANCY_MODE:-db-per-tenant-org}}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg}}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

printf "==============================================\n"
printf "CAD Capabilities Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity\n"
env \
  YUANTUS_TENANCY_MODE="$TENANCY_MODE" \
  YUANTUS_DATABASE_URL="$DB_URL" \
  YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE" \
  YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL" \
  "$CLI" seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null

printf "\n==> Login\n"
API="$BASE_URL/api/v1"
TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$TOKEN" ]]; then
  echo "FAIL: Admin login failed" >&2
  exit 1
fi
AUTH=(-H "Authorization: Bearer $TOKEN")
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

printf "\n==> Capabilities endpoint\n"
$CURL "$API/cad/capabilities" "${AUTH[@]}" "${HEADERS[@]}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("counts");assert d.get("features");assert d.get("formats");assert d.get("extensions");print("OK: capabilities payload")'

printf "\n==============================================\n"
printf "CAD Capabilities Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
