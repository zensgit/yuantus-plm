#!/usr/bin/env bash
# =============================================================================
# CAD Sync Template Verification Script
# Verifies CSV template export/import for CAD-synced fields.
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"
DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
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

TS="$(date +%s)"
TEMPLATE_FILE="/tmp/yuantus_sync_template_${TS}.csv"
UPDATE_FILE="/tmp/yuantus_sync_template_update_${TS}.csv"

cleanup() {
  rm -f "$TEMPLATE_FILE" "$UPDATE_FILE"
}
trap cleanup EXIT

echo "=============================================="
echo "CAD Sync Template Verification"
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
echo "==> Download CAD sync template"
$CURL "$API/cad/sync-template/Part" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" > "$TEMPLATE_FILE"
if [[ ! -s "$TEMPLATE_FILE" ]]; then
  fail "Template download failed"
fi
ok "Template downloaded"

echo ""
echo "==> Build update template"
cat > "$UPDATE_FILE" <<'CSV'
property_name,label,data_type,is_cad_synced,cad_key
item_number,Part Number,string,true,part_number
description,Description,string,true,description
CSV
ok "Template updated"

echo ""
echo "==> Apply template"
APPLY_RESP="$($CURL -X POST "$API/cad/sync-template/Part" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -F "file=@$UPDATE_FILE;filename=sync_template.csv")"
UPDATED=$(echo "$APPLY_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("updated",0))')
if [[ "$UPDATED" -lt 1 ]]; then
  echo "Response: $APPLY_RESP" >&2
  fail "Template apply failed"
fi
ok "Template applied"

echo ""
echo "==> Verify Part ItemType properties"
ITEMTYPE_JSON="$($CURL "$API/meta/item-types/Part" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
if [[ -z "$ITEMTYPE_JSON" ]]; then
  fail "ItemType response empty"
fi
VERIFY=$(
  RESP_JSON="$ITEMTYPE_JSON" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
item = json.loads(raw)
props = {p.get("name"): p for p in item.get("properties", [])}
item_number = props.get("item_number") or {}
description = props.get("description") or {}
if not item_number.get("is_cad_synced"):
    print("FAIL:item_number not synced")
    raise SystemExit(0)
if not description.get("is_cad_synced"):
    print("FAIL:description not synced")
    raise SystemExit(0)
ui_opts = item_number.get("ui_options") or {}
if isinstance(ui_opts, str):
    try:
        ui_opts = json.loads(ui_opts)
    except Exception:
        ui_opts = {}
if ui_opts.get("cad_key") != "part_number":
    print("FAIL:item_number cad_key mismatch")
    raise SystemExit(0)
print("OK")
PY
)
if [[ "$VERIFY" != "OK" ]]; then
  echo "$VERIFY" >&2
  fail "Property verification failed"
fi
ok "Property mapping verified"

echo ""
echo "=============================================="
echo "CAD Sync Template Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
