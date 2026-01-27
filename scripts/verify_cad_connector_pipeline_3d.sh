#!/usr/bin/env bash
# =============================================================================
# CAD 3D Connector Pipeline Verification
# - upload 3D assembly
# - trigger preview/geometry/extract/bom jobs
# - verify artifacts + bom import
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:7910}"
TENANT="${2:-tenant-1}"
ORG="${3:-org-1}"

CLI="${CLI:-.venv/bin/yuantus}"
PY="${PY:-.venv/bin/python}"
CURL="${CURL:-curl -sS}"

DB_URL="${DB_URL:-${YUANTUS_DATABASE_URL:-}}"
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-}}"

CAD_CONNECTOR_BASE_URL="${CAD_CONNECTOR_BASE_URL:-http://127.0.0.1:8300}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "Missing python3 (set PY=...)" >&2
    exit 2
  fi
fi

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if ! curl -fsS "${CAD_CONNECTOR_BASE_URL%/}/health" >/dev/null 2>&1; then
  fail "CAD connector not reachable at ${CAD_CONNECTOR_BASE_URL%/}/health"
fi

run_cli() {
  local identity_url="$IDENTITY_DB_URL"
  if [[ -z "$identity_url" && -n "$DB_URL" ]]; then
    identity_url="$DB_URL"
  fi
  if [[ -n "$DB_URL" || -n "$identity_url" ]]; then
    env \
      ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

API="$BASE_URL/api/v1"
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")

echo "=============================================="
echo "CAD 3D Connector Pipeline Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "CAD_CONNECTOR_BASE_URL: $CAD_CONNECTOR_BASE_URL"
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
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token", ""))'
)"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
ok "Admin login"

echo ""
echo "==> Upload assembly with pipeline jobs"
TS="$(date +%s)"
ASM_FILE="/tmp/yuantus_connector_asm_$TS.sldasm"
echo "Yuantus CAD connector assembly $TS" > "$ASM_FILE"

RESP="$(
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$ASM_FILE;filename=yuantus_asm_$TS.sldasm" \
    -F "file_role=native_cad" \
    -F "create_preview_job=true" \
    -F "create_geometry_job=true" \
    -F "create_extract_job=true" \
    -F "create_bom_job=true" \
    -F "auto_create_part=true"
)"

rm -f "$ASM_FILE"

FILE_ID="$(echo "$RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id", ""))')"
ITEM_ID="$(echo "$RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("item_id", ""))')"
if [[ -z "$FILE_ID" || -z "$ITEM_ID" ]]; then
  echo "Response: $RESP" >&2
  fail "cad/import missing file_id or item_id"
fi
ok "Uploaded file: $FILE_ID (item_id=$ITEM_ID)"

wait_for_ok() {
  local label="$1"
  local url="$2"
  local attempts="${3:-30}"
  local sleep_s="${4:-2}"
  for _ in $(seq 1 "$attempts"); do
    local status
    status="$($CURL -o /dev/null -w '%{http_code}' "$url" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" || true)"
    if [[ "$status" == "200" || "$status" == "302" ]]; then
      ok "$label"
      return 0
    fi
    sleep "$sleep_s"
  done
  fail "$label not ready ($url)"
}

wait_for_ok "Preview ready" "$API/file/$FILE_ID/preview"
wait_for_ok "Geometry ready" "$API/file/$FILE_ID/geometry"

echo ""
echo "==> Check BOM import"
found_bom=0
for _ in $(seq 1 30); do
  BOM_RAW="$($CURL "$API/cad/files/$FILE_ID/bom" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" 2>/dev/null || true)"
  if [[ -n "$BOM_RAW" ]]; then
    STATUS="$(
      RAW_JSON="$BOM_RAW" "$PY" - <<'PY'
import json, os
raw = os.environ.get("RAW_JSON", "")
try:
    data = json.loads(raw)
except Exception:
    print("0")
    raise SystemExit(0)
result = data.get("import_result") or {}
print("1" if (result.get("created_lines", 0) >= 1) else "0")
PY
    )"
    if [[ "$STATUS" == "1" ]]; then
      ok "BOM imported"
      found_bom=1
      break
    fi
  fi
  sleep 2
done
if [[ "$found_bom" != "1" ]]; then
  fail "BOM import not completed"
fi

echo ""
echo "=============================================="
echo "CAD 3D Connector Pipeline Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
