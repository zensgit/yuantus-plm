#!/usr/bin/env bash
# =============================================================================
# DocDoku Alignment Verification
# Verifies: preview + metadata endpoints and connector list (DocDoku-style mapping).
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
DB_URL_TEMPLATE="${DB_URL_TEMPLATE:-${YUANTUS_DATABASE_URL_TEMPLATE:-}}"
IDENTITY_DB_URL="${IDENTITY_DB_URL:-${YUANTUS_IDENTITY_DATABASE_URL:-postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg}}"

if [[ -z "$DB_URL_TEMPLATE" ]]; then
  DB_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}"
fi

# Avoid Python .format errors by pre-resolving template placeholders for this run.
if [[ "$DB_URL_TEMPLATE" == *"{"* ]]; then
  DB_URL_TEMPLATE="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
  DB_URL_TEMPLATE="${DB_URL_TEMPLATE//\{org_id\}/$ORG}"
fi

CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-${YUANTUS_CAD_ML_BASE_URL:-http://localhost:8001}}"
CAD_ML_HEALTH_URL="${CAD_ML_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/vision/health}"
CAD_PREVIEW_ALLOW_FALLBACK="${CAD_PREVIEW_ALLOW_FALLBACK:-0}"

STORAGE_TYPE="${STORAGE_TYPE:-${YUANTUS_STORAGE_TYPE:-s3}}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-${YUANTUS_S3_ENDPOINT_URL:-http://localhost:59000}}"
S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-http://localhost:59000}}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${YUANTUS_S3_BUCKET_NAME:-yuantus}}"
S3_ACCESS_KEY_ID="${S3_ACCESS_KEY_ID:-${YUANTUS_S3_ACCESS_KEY_ID:-minioadmin}}"
S3_SECRET_ACCESS_KEY="${S3_SECRET_ACCESS_KEY:-${YUANTUS_S3_SECRET_ACCESS_KEY:-minioadmin}}"

SAMPLE_FILE="${CAD_PREVIEW_SAMPLE_FILE:-/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg}"

if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "SKIP: Sample file not found: $SAMPLE_FILE" >&2
  exit 0
fi

normalize_http_code() {
  local http_code="${1:-}"
  if [[ ! "$http_code" =~ ^[0-9]{3}$ ]]; then
    echo "000"
    return 0
  fi
  echo "$http_code"
}

HTTP_CODE="$(normalize_http_code "$($CURL -o /dev/null -w '%{http_code}' "$CAD_ML_HEALTH_URL" 2>/dev/null || true)")"
if [[ "$HTTP_CODE" != "200" ]]; then
  if [[ "$CAD_PREVIEW_ALLOW_FALLBACK" == "1" ]]; then
    echo "WARN: CAD ML Vision not available at $CAD_ML_HEALTH_URL (HTTP $HTTP_CODE)"
    echo "      Continuing with fallback preview."
  else
    echo "SKIP: CAD ML Vision not available at $CAD_ML_HEALTH_URL (HTTP $HTTP_CODE)"
    exit 0
  fi
fi

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

printf "==============================================\n"
printf "DocDoku Alignment Verification\n"
printf "BASE_URL: %s\n" "$BASE_URL"
printf "TENANT: %s, ORG: %s\n" "$TENANT" "$ORG"
printf "SAMPLE: %s\n" "$SAMPLE_FILE"
printf "==============================================\n"

printf "\n==> Login\n"
API="$BASE_URL/api/v1"
TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$TOKEN" ]]; then
  fail "Admin login failed (run seed-identity first)"
fi
AUTH=(-H "Authorization: Bearer $TOKEN")
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")
ok "Admin login"

printf "\n==> CAD connectors list\n"
$CURL "$API/cad/connectors" "${AUTH[@]}" "${HEADERS[@]}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert len(d)>0;print(f"Connectors: {len(d)}")'

printf "\n==> CAD capabilities\n"
$CURL "$API/cad/capabilities" "${AUTH[@]}" "${HEADERS[@]}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("counts");assert d.get("features");print("Capabilities OK")'

printf "\n==> Upload CAD file (create preview/extract jobs)\n"
RESP="$($CURL -X POST "$API/cad/import" \
  "${AUTH[@]}" "${HEADERS[@]}" \
  -F "file=@$SAMPLE_FILE;filename=$(basename "$SAMPLE_FILE")" \
  -F "create_extract_job=true" \
  -F "create_preview_job=true" \
  -F "create_geometry_job=false" \
  -F "create_dedup_job=false" \
  -F "create_ml_job=false")"
FILE_ID=$(echo "$RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')
[[ -n "$FILE_ID" ]] || fail "Import failed: $RESP"
ok "Uploaded file: $FILE_ID"

printf "\n==> Wait for preview/extract jobs\n"
READY=0
for i in $(seq 1 20); do
  META="$($CURL "$API/file/$FILE_ID" "${AUTH[@]}" "${HEADERS[@]}")"
  PREVIEW_URL="$(echo "$META" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("preview_url"))')"
  METADATA_URL="$(echo "$META" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("cad_metadata_url"))')"
  if [[ "$PREVIEW_URL" != "None" && "$METADATA_URL" != "None" && -n "$PREVIEW_URL" && -n "$METADATA_URL" ]]; then
    READY=1
    break
  fi
  sleep 1
done
if [[ "$READY" != "1" ]]; then
  fail "preview/metadata not ready (jobs may be pending)"
fi
ok "preview + metadata ready"

printf "\n==> Fetch file metadata\n"
META="$($CURL "$API/file/$FILE_ID" "${AUTH[@]}" "${HEADERS[@]}")"
$PY - <<PY
import json,sys
meta=json.loads("""$META""")
if not meta.get("preview_url"):
    raise SystemExit("FAIL: preview_url missing")
if not meta.get("cad_metadata_url"):
    raise SystemExit("FAIL: cad_metadata_url missing")
print("OK: preview_url + cad_metadata_url")
PY

printf "\n==> Preview endpoint\n"
HTTP_CODE="$($CURL -o /dev/null -w '%{http_code}' "$API/file/$FILE_ID/preview" "${AUTH[@]}" "${HEADERS[@]}")"
if [[ "$HTTP_CODE" != "200" && "$HTTP_CODE" != "302" ]]; then
  fail "preview endpoint unexpected HTTP $HTTP_CODE"
fi
ok "Preview endpoint HTTP $HTTP_CODE"

printf "\n==> CAD attributes endpoint\n"
$CURL "$API/cad/files/$FILE_ID/attributes" "${AUTH[@]}" "${HEADERS[@]}" \
  | "$PY" -c 'import sys,json;d=json.load(sys.stdin);assert d.get("file_id");print("OK: attributes endpoint")'

printf "\n==============================================\n"
printf "DocDoku Alignment Verification Complete\n"
printf "==============================================\n"
printf "ALL CHECKS PASSED\n"
