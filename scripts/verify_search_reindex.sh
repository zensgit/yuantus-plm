#!/usr/bin/env bash
# =============================================================================
# Search Reindex Verification Script
# Verifies search status + reindex flow (admin-only).
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

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

wait_for_search() {
  local query="$1"
  local item_id="$2"

  for _ in {1..10}; do
    RESP="$($CURL "$API/search/?q=$query&item_type=Part" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
    if RESP_JSON="$RESP" ITEM_ID="$item_id" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "{}")
data = json.loads(raw)
item_id = os.environ.get("ITEM_ID", "")
if not item_id:
    raise SystemExit(1)
found = any(hit.get("id") == item_id for hit in data.get("hits") or [])
raise SystemExit(0 if found else 1)
PY
    then
      return 0
    fi
    sleep 1
  done
  return 1
}

TS="$(date +%s)"

echo "=============================================="
echo "Search Reindex Verification"
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
ADMIN_TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

echo ""
echo "==> Create Part item"
ITEM_NUMBER="REINDEX-$TS"
ITEM_ID="$($CURL -X POST "$API/aml/apply" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$ITEM_NUMBER\",\"name\":\"Reindex Item $TS\"}}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')"
if [[ -z "$ITEM_ID" ]]; then
  fail "Failed to create Part item"
fi
ok "Created Part: $ITEM_ID"

echo ""
echo "==> Search status"
STATUS_JSON="$($CURL "$API/search/status" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
ENGINE="$($PY -c 'import sys,json;print(json.load(sys.stdin).get("engine",""))' <<<"$STATUS_JSON")"
if [[ -z "$ENGINE" ]]; then
  fail "Search status missing engine"
fi
ok "Search engine: $ENGINE"

echo ""
echo "==> Reindex"
REINDEX_JSON="$($CURL -X POST "$API/search/reindex" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d '{"item_type_id":"Part","reset":false,"limit":200,"batch_size":200}')"
OK_FLAG="$($PY -c 'import sys,json;print(json.load(sys.stdin).get("ok",False))' <<<"$REINDEX_JSON")"
INDEXED="$($PY -c 'import sys,json;print(json.load(sys.stdin).get("indexed",0))' <<<"$REINDEX_JSON")"
if [[ "$OK_FLAG" != "True" ]]; then
  echo "Response: $REINDEX_JSON" >&2
  fail "Reindex failed"
fi
if [[ "$INDEXED" -lt 1 ]]; then
  echo "Response: $REINDEX_JSON" >&2
  fail "Reindex indexed count too low"
fi
ok "Reindex completed (indexed=$INDEXED)"

echo ""
echo "==> Search by item_number"
if wait_for_search "$ITEM_NUMBER" "$ITEM_ID"; then
  ok "Search found item after reindex"
else
  fail "Search did not find item after reindex"
fi

echo ""
echo "==> Cleanup"
$CURL -X POST "$API/aml/apply" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"delete\",\"id\":\"$ITEM_ID\"}" >/dev/null
ok "Deleted item"

echo ""
echo "=============================================="
echo "Search Reindex Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
