#!/usr/bin/env bash
# =============================================================================
# CAD 2D Connectors Verification Script
# Verifies GStarCAD/ZWCAD/Haochen/Zhongwang uploads via /cad/import (override + auto-detect).
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

echo "=============================================="
echo "CAD 2D Connectors Verification"
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
echo "==> Create dummy DWG/DXF files"
DWG_FILE="/tmp/yuantus_gstarcad_$TS.dwg"
DXF_FILE="/tmp/yuantus_zwcad_$TS.dxf"
DWG_ALIAS_FILE="/tmp/yuantus_haochencad_$TS.dwg"
DXF_ALIAS_FILE="/tmp/yuantus_zhongwang_$TS.dxf"
AUTO_FILE="/tmp/yuantus_cad_auto_$TS.dwg"
AUTO_ZW_FILE="/tmp/yuantus_cad_auto_zw_$TS.dwg"
echo "DWG placeholder $TS" > "$DWG_FILE"
echo "DXF placeholder $TS" > "$DXF_FILE"
echo "DWG Haochen placeholder $TS" > "$DWG_ALIAS_FILE"
echo "DXF Zhongwang placeholder $TS" > "$DXF_ALIAS_FILE"
printf "浩辰CAD\n图号=HC-AUTO-%s\n名称=自动识别测试\n材料=钢\n版本=A\n重量=1.2\n" "$TS" > "$AUTO_FILE"
printf "ZWCAD\n图号=ZW-AUTO-%s\n名称=中望自动识别\n材料=铝\n版本=B\n重量=1200g\n" "$TS" > "$AUTO_ZW_FILE"
ok "Created files: $DWG_FILE, $DXF_FILE, $DWG_ALIAS_FILE, $DXF_ALIAS_FILE, $AUTO_FILE, $AUTO_ZW_FILE"

upload_and_check() {
  local file_path="$1"
  local filename="$2"
  local cad_vendor="$3"
  local expected_vendor="$4"
  local expected_ext="$5"
  local expected_connector="$6"
  local cad_form=()
  local vendor_label="$cad_vendor"
  if [[ -z "$vendor_label" ]]; then
    vendor_label="auto-detect"
  fi
  if [[ -n "$cad_vendor" ]]; then
    cad_form=(-F "cad_format=$cad_vendor")
  fi

  echo ""
  echo "==> Upload $filename ($vendor_label)"
  RESP="$(
    $CURL -X POST "$API/cad/import" \
      "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
      -F "file=@$file_path;filename=$filename" \
      "${cad_form[@]}" \
      -F "file_role=drawing" \
      -F "create_preview_job=false" \
      -F "create_geometry_job=false" \
      -F "create_dedup_job=false" \
      -F "create_ml_job=false"
  )"
  FILE_ID="$(echo "$RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')"
  if [[ -z "$FILE_ID" ]]; then
    echo "Response: $RESP"
    fail "Upload failed for $cad_vendor"
  fi
  ok "Uploaded file: $FILE_ID"

  META="$($CURL "$API/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
  RESP_JSON="$META" EXPECT_VENDOR="$expected_vendor" EXPECT_EXT="$expected_ext" EXPECT_CONNECTOR="$expected_connector" "$PY" - <<'PY'
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
if doc_type != "2d":
    raise SystemExit(f"document_type mismatch: {doc_type} != 2d")
if not is_native:
    raise SystemExit("expected is_native_cad=true")
if expected_connector and connector != expected_connector:
    raise SystemExit(f"cad_connector_id mismatch: {connector} != {expected_connector}")
print("Metadata OK")
PY
  ok "Metadata verified ($expected_vendor)"
}

upload_and_check "$DWG_FILE" "gstarcad_$TS.dwg" "GSTARCAD" "GSTARCAD" "dwg" "gstarcad"
upload_and_check "$DXF_FILE" "zwcad_$TS.dxf" "ZWCAD" "ZWCAD" "dxf" "zwcad"
upload_and_check "$DWG_ALIAS_FILE" "haochencad_$TS.dwg" "HAOCHEN" "HAOCHEN" "dwg" "haochencad"
upload_and_check "$DXF_ALIAS_FILE" "zhongwangcad_$TS.dxf" "ZHONGWANG" "ZHONGWANG" "dxf" "zhongwangcad"
upload_and_check "$AUTO_FILE" "cad_auto_$TS.dwg" "" "HAOCHEN" "dwg" "haochencad"
upload_and_check "$AUTO_ZW_FILE" "cad_auto_zw_$TS.dwg" "" "ZWCAD" "dwg" "zwcad"

echo ""
echo "==> Cleanup"
rm -f "$DWG_FILE" "$DXF_FILE" "$DWG_ALIAS_FILE" "$DXF_ALIAS_FILE" "$AUTO_FILE" "$AUTO_ZW_FILE"
ok "Cleaned up temp files"

echo ""
echo "=============================================="
echo "CAD 2D Connectors Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
