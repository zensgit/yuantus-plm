#!/usr/bin/env bash
# =============================================================================
# CAD Connectors Config Verification Script
# Verifies reload of custom connectors from JSON config.
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
DEMO_FILE="/tmp/yuantus_demo_${TS}.dmo"

cleanup() {
  rm -f "$DEMO_FILE"
}
trap cleanup EXIT

CONFIG_JSON="$(cat <<'JSON'
{
  "config": {
    "connectors": [
      {
        "id": "demo-cad",
        "label": "DemoCAD",
        "cad_format": "DEMO_CAD",
        "document_type": "2d",
        "extensions": ["dmo"],
        "aliases": ["DEMO"],
        "priority": 50,
        "description": "Demo connector from config",
        "signature_tokens": ["DEMO CAD", "DEMO-CAD"],
        "kind": "keyvalue",
        "key_aliases": {
          "part_number": "part_number",
          "description": "description",
          "revision": "revision"
        }
      }
    ]
  }
}
JSON
)"

cat > "$DEMO_FILE" <<'DEMO'
part_number=DEMO-001
description=Demo CAD Part
revision=A
DEMO

echo "=============================================="
echo "CAD Connectors Config Verification"
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
echo "==> Reload connectors from config"
RELOAD_RAW="$($CURL -w 'HTTPSTATUS:%{http_code}' -X POST "$API/cad/connectors/reload" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "$CONFIG_JSON")"
RELOAD_BODY="${RELOAD_RAW%HTTPSTATUS:*}"
RELOAD_STATUS="${RELOAD_RAW##*HTTPSTATUS:}"
if [[ "$RELOAD_STATUS" != "200" ]]; then
  echo "Response: $RELOAD_BODY" >&2
  fail "Reload failed (status=$RELOAD_STATUS)."
fi
CUSTOM_COUNT=$(echo "$RELOAD_BODY" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("custom_loaded",0))')
if [[ "$CUSTOM_COUNT" -lt 1 ]]; then
  fail "Custom connectors not loaded"
fi
ok "Reloaded connectors (custom_loaded=$CUSTOM_COUNT)"

echo ""
echo "==> Verify connector listing"
LIST_JSON="$($CURL "$API/cad/connectors" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
HAS_DEMO=$(echo "$LIST_JSON" | "$PY" -c 'import sys,json;data=json.load(sys.stdin);print(any(i.get("id")=="demo-cad" for i in data))')
if [[ "$HAS_DEMO" != "True" ]]; then
  fail "demo-cad not found in connector list"
fi
ok "Connector list includes demo-cad"

echo ""
echo "==> Import DEMO CAD file"
IMPORT_RESP="$($CURL -X POST "$API/cad/import" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -F "file=@$DEMO_FILE;filename=demo_$TS.dmo" \
  -F "create_preview_job=false" \
  -F "create_geometry_job=false" \
  -F "create_extract_job=false" \
  -F "create_dedup_job=false" \
  -F "create_ml_job=false")"
FILE_ID=$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')
FORMAT=$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_format",""))')
CONNECTOR_ID=$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_connector_id",""))')
if [[ -z "$FILE_ID" || "$FORMAT" != "DEMO_CAD" || "$CONNECTOR_ID" != "demo-cad" ]]; then
  echo "Response: $IMPORT_RESP" >&2
  fail "cad_format/connector_id mismatch"
fi
ok "cad_format/connector_id resolved via config"
ok "Imported file: $FILE_ID"

echo ""
echo "=============================================="
echo "CAD Connectors Config Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
