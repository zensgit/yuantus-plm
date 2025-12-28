#!/usr/bin/env bash
# =============================================================================
# Search Index Verification Script
# Verifies: item add/update/delete reflected in search results.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-}"
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

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

urlencode() {
  "$PY" - <<'PY' "$1"
import sys
import urllib.parse

print(urllib.parse.quote_plus(sys.argv[1]))
PY
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

wait_for_search() {
  local query="$1"
  local item_id="$2"
  local prop_key="$3"
  local prop_value="$4"
  local expect_found="$5"

  local encoded
  encoded="$(urlencode "$query")"
  for _ in {1..10}; do
    RESP="$($CURL "$API/search/?q=$encoded&item_type=Part" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
    if RESP_JSON="$RESP" ITEM_ID="$item_id" PROP_KEY="$prop_key" PROP_VALUE="$prop_value" EXPECT_FOUND="$expect_found" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "{}")
data = json.loads(raw)
hits = data.get("hits") or []
total = data.get("total", 0)
expect_found = os.environ.get("EXPECT_FOUND") == "1"
item_id = os.environ.get("ITEM_ID", "")
prop_key = os.environ.get("PROP_KEY", "")
prop_value = os.environ.get("PROP_VALUE", "")

def hit_matches(hit):
    if item_id and hit.get("id") == item_id:
        return True
    props = hit.get("properties") or {}
    if prop_key and prop_value and props.get(prop_key) == prop_value:
        return True
    return False

found = any(hit_matches(hit) for hit in hits)
if expect_found:
    if total < 1 or not found:
        raise SystemExit(1)
else:
    if total > 0 and found:
        raise SystemExit(1)
PY
    then
      return 0
    fi
    sleep 1
  done
  return 1
}

echo "=============================================="
echo "Search Index Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
ADMIN_TOKEN="$(
  $CURL -X POST "$API/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

TS="$(date +%s)"

echo ""
echo "==> Create Part item"
ITEM_NUMBER="SEARCH-$TS"
ITEM_NAME="Search Item $TS"
ITEM_ID="$(
  $CURL -X POST "$API/aml/apply" \
    -H 'content-type: application/json' \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$ITEM_NUMBER\",\"name\":\"$ITEM_NAME\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ITEM_ID" ]]; then
  fail "Failed to create Part item"
fi
ok "Created Part: $ITEM_ID"

echo ""
echo "==> Search by item_number"
if wait_for_search "$ITEM_NUMBER" "$ITEM_ID" "item_number" "$ITEM_NUMBER" "1"; then
  ok "Search found item by item_number"
else
  fail "Search did not find item by item_number"
fi

echo ""
echo "==> Update item name and re-search"
NEW_NAME="Search Item Updated $TS"
$CURL -X POST "$API/aml/apply" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"$ITEM_ID\",\"properties\":{\"name\":\"$NEW_NAME\"}}" >/dev/null

if wait_for_search "$NEW_NAME" "$ITEM_ID" "name" "$NEW_NAME" "1"; then
  ok "Search found item after update"
else
  fail "Search did not reflect updated name"
fi

echo ""
echo "==> Delete item and verify search removal"
$CURL -X POST "$API/aml/apply" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"delete\",\"id\":\"$ITEM_ID\"}" >/dev/null

if wait_for_search "$ITEM_NUMBER" "$ITEM_ID" "item_number" "$ITEM_NUMBER" "0"; then
  ok "Search removal validated"
else
  fail "Deleted item still appears in search"
fi

echo ""
echo "=============================================="
echo "Search Index Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
