#!/usr/bin/env bash
# =============================================================================
# Search ECO Verification Script
# Verifies: /search/ecos returns ECOs by name/state (admin-only).
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

TENANCY_MODE="${YUANTUS_TENANCY_MODE:-${TENANCY_MODE:-single}}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
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
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

if [[ "$TENANCY_MODE" == "db-per-tenant-org" && -n "$DB_URL_TEMPLATE" ]]; then
  DB_URL="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
  DB_URL="${DB_URL//\{org_id\}/$ORG}"
elif [[ "$TENANCY_MODE" == "db-per-tenant" && -n "$DB_URL_TEMPLATE" ]]; then
  DB_URL="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
  DB_URL="${DB_URL//\{org_id\}/default}"
fi

if [[ -z "$DB_URL" ]]; then
  DB_URL="$(
    TENANT="$TENANT" ORG="$ORG" "$PY" - <<'PY'
import os
from yuantus.config import get_settings
from yuantus.database import resolve_database_url

tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")
settings = get_settings()
try:
    url = resolve_database_url(tenant_id=tenant, org_id=org)
except Exception:
    url = settings.DATABASE_URL
print(url or "")
PY
  )"
fi

run_cli() {
  env \
    ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
    ${IDENTITY_DB_URL:+YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"} \
    ${TENANCY_MODE:+YUANTUS_TENANCY_MODE="$TENANCY_MODE"} \
    ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
    "$CLI" "$@"
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "Search ECO Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "==============================================\n"

printf "\n==> Seed identity/meta\n"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null
ok "Seeded identity/meta"

printf "\n==> Login as admin\n"
TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token", ""))')"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH=(-H "Authorization: Bearer $TOKEN")
ok "Admin login"

printf "\n==> Search ECO index status\n"
STATUS_JSON="$($CURL "$API/search/ecos/status" "${HEADERS[@]}" "${AUTH[@]}")"
ENGINE="$(
  STATUS_JSON="$STATUS_JSON" "$PY" - <<'PY'
import os, json
data = json.loads(os.environ.get("STATUS_JSON", "{}"))
print(data.get("engine", "db"))
PY
)"
ok "Search ECO engine: $ENGINE"

if [[ "$ENGINE" != "db" ]]; then
  printf "\n==> Reindex ECO search\n"
  REINDEX_JSON="$($CURL -X POST "$API/search/ecos/reindex" "${HEADERS[@]}" "${AUTH[@]}" \
    -H 'content-type: application/json' \
    -d '{"reset":true,"limit":200}')"
  REINDEX_OK="$(
    REINDEX_JSON="$REINDEX_JSON" "$PY" - <<'PY'
import os, json
data = json.loads(os.environ.get("REINDEX_JSON", "{}"))
print("1" if data.get("ok") else "0")
PY
  )"
  if [[ "$REINDEX_OK" != "1" ]]; then
    echo "Response: $REINDEX_JSON" >&2
    fail "Reindex ECO search failed"
  fi
  ok "Reindex ECO search"
fi

TS="$(date +%s)"
ECO_NAME="ECO-SEARCH-$TS"

printf "\n==> Create ECO product\n"
PRODUCT_ID="$($CURL -X POST "$API/aml/apply" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ECO-P-$TS\",\"name\":\"ECO Product\"}}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id", ""))')"
if [[ -z "$PRODUCT_ID" ]]; then
  fail "Failed to create ECO product"
fi
ok "Created ECO product: $PRODUCT_ID"

printf "\n==> Create ECO\n"
ECO_RESP="$($CURL -X POST "$API/eco" "${HEADERS[@]}" "${AUTH[@]}" \
  -H 'content-type: application/json' \
  -d "{\"name\":\"$ECO_NAME\",\"eco_type\":\"bom\",\"product_id\":\"$PRODUCT_ID\",\"description\":\"search test $TS\"}")"
ECO_ID="$(echo "$ECO_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id", ""))')"
if [[ -z "$ECO_ID" ]]; then
  echo "Response: $ECO_RESP" >&2
  fail "Failed to create ECO"
fi
ok "Created ECO: $ECO_ID"

printf "\n==> Search ECO by name\n"
SEARCH_RESP="$($CURL "$API/search/ecos?q=$ECO_NAME&limit=10" "${HEADERS[@]}" "${AUTH[@]}")"
NAME_OK="$(RESP_JSON="$SEARCH_RESP" ECO_ID="$ECO_ID" ECO_NAME="$ECO_NAME" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", "{}"))
search_id = os.environ.get("ECO_ID")
search_name = os.environ.get("ECO_NAME")
if resp.get("total", 0) < 1:
    print("0")
    raise SystemExit(0)
for hit in resp.get("hits", []) or []:
    if hit.get("id") == search_id and hit.get("name") == search_name:
        print("1")
        raise SystemExit(0)
print("0")
PY
)"
if [[ "$NAME_OK" != "1" ]]; then
  echo "Response: $SEARCH_RESP" >&2
  fail "Search ECO by name failed"
fi
ok "Search by name"

printf "\n==> Search ECO by state\n"
STATE_RESP="$($CURL "$API/search/ecos?q=$ECO_NAME&state=draft&limit=10" "${HEADERS[@]}" "${AUTH[@]}")"
STATE_OK="$(RESP_JSON="$STATE_RESP" ECO_ID="$ECO_ID" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", "{}"))
search_id = os.environ.get("ECO_ID")
for hit in resp.get("hits", []) or []:
    if hit.get("id") == search_id and hit.get("state") == "draft":
        print("1")
        raise SystemExit(0)
print("0")
PY
)"
if [[ "$STATE_OK" != "1" ]]; then
  echo "Response: $STATE_RESP" >&2
  fail "Search ECO by state failed"
fi
ok "Search by state"

printf "\n==============================================\n"
printf "Search ECO Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
