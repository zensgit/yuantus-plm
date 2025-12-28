#!/usr/bin/env bash
# =============================================================================
# CAD 3D Connectors Verification Script
# Verifies SolidWorks/NX/Creo/CATIA/Inventor uploads via /cad/import.
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
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"

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
      ${DB_URL_TEMPLATE:+YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

echo "=============================================="
echo "CAD 3D Connectors Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "=============================================="

TS="$(date +%s)"

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

echo ""
echo "==> Create dummy 3D files"
SW_PART="/tmp/yuantus_sw_part_$TS.sldprt"
SW_ASM="/tmp/yuantus_sw_asm_$TS.sldasm"
NX_PRT="/tmp/yuantus_nx_$TS.prt"
CREO_PRT="/tmp/yuantus_creo_$TS.prt"
CAT_PART="/tmp/yuantus_catia_$TS.catpart"
INV_PART="/tmp/yuantus_inv_$TS.ipt"
AUTO_PRT="/tmp/yuantus_auto_$TS.prt"
echo "SolidWorks placeholder $TS" > "$SW_PART"
echo "SolidWorks assembly placeholder $TS" > "$SW_ASM"
echo "NX placeholder $TS" > "$NX_PRT"
echo "Creo placeholder $TS" > "$CREO_PRT"
echo "CATIA placeholder $TS" > "$CAT_PART"
echo "Inventor placeholder $TS" > "$INV_PART"
echo "Auto detect placeholder $TS" > "$AUTO_PRT"
ok "Created files"

upload_and_check() {
  local file_path="$1"
  local filename="$2"
  local cad_format="$3"
  local cad_connector_id="$4"
  local expected_format="$5"
  local expected_ext="$6"
  local expected_connector="$7"

  local form_fields=()
  if [[ -n "$cad_format" ]]; then
    form_fields+=(-F "cad_format=$cad_format")
  fi
  if [[ -n "$cad_connector_id" ]]; then
    form_fields+=(-F "cad_connector_id=$cad_connector_id")
  fi

  echo ""
  echo "==> Upload $filename"
  RESP="$(
    $CURL -X POST "$API/cad/import" \
      "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      -F "file=@$file_path;filename=$filename" \
      "${form_fields[@]}" \
      -F "file_role=native_cad" \
      -F "create_preview_job=false" \
      -F "create_geometry_job=false" \
      -F "create_dedup_job=false" \
      -F "create_ml_job=false"
  )"
  FILE_ID="$(echo "$RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')"
  if [[ -z "$FILE_ID" ]]; then
    echo "Response: $RESP"
    fail "Upload failed"
  fi
  ok "Uploaded file: $FILE_ID"

  META="$($CURL "$API/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  RESP_JSON="$META" EXPECT_VENDOR="$expected_format" EXPECT_EXT="$expected_ext" EXPECT_CONNECTOR="$expected_connector" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "")
data = json.loads(raw)
vendor = data.get("cad_format")
ext = data.get("file_type")
doc_type = data.get("document_type")
is_native = data.get("is_native_cad")
connector = data.get("cad_connector_id")
expected_vendor = os.environ.get("EXPECT_VENDOR")
expected_ext = os.environ.get("EXPECT_EXT")
expected_connector = os.environ.get("EXPECT_CONNECTOR")
if vendor != expected_vendor:
    raise SystemExit(f"cad_format mismatch: {vendor} != {expected_vendor}")
if ext != expected_ext:
    raise SystemExit(f"file_type mismatch: {ext} != {expected_ext}")
if doc_type != "3d":
    raise SystemExit(f"document_type mismatch: {doc_type} != 3d")
if not is_native:
    raise SystemExit("expected is_native_cad=true")
if expected_connector and connector != expected_connector:
    raise SystemExit(f"cad_connector_id mismatch: {connector} != {expected_connector}")
print("Metadata OK")
PY
  ok "Metadata verified ($expected_format)"
}

upload_and_check "$SW_PART" "solidworks_part_$TS.sldprt" "" "" "SOLIDWORKS" "sldprt" "solidworks"
upload_and_check "$SW_ASM" "solidworks_asm_$TS.sldasm" "" "" "SOLIDWORKS" "sldasm" "solidworks"
upload_and_check "$NX_PRT" "nx_$TS.prt" "NX" "" "NX" "prt" "nx"
upload_and_check "$CREO_PRT" "creo_$TS.prt" "" "creo" "CREO" "prt" "creo"
upload_and_check "$CAT_PART" "catia_$TS.catpart" "" "" "CATIA" "catpart" "catia"
upload_and_check "$INV_PART" "inventor_$TS.ipt" "" "" "INVENTOR" "ipt" "inventor"
upload_and_check "$AUTO_PRT" "auto_$TS.prt" "" "" "NX" "prt" "nx"

echo ""
echo "==> Cleanup"
rm -f "$SW_PART" "$SW_ASM" "$NX_PRT" "$CREO_PRT" "$CAT_PART" "$INV_PART" "$AUTO_PRT"
ok "Cleaned up temp files"

echo ""
echo "=============================================="
echo "CAD 3D Connectors Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
