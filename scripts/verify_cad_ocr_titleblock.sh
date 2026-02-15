#!/usr/bin/env bash
# =============================================================================
# CAD OCR Title Block Verification Script
# Requires CAD ML Vision service to be available.
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

STORAGE_TYPE="${STORAGE_TYPE:-${YUANTUS_STORAGE_TYPE:-}}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-${YUANTUS_S3_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}}"
S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${YUANTUS_S3_BUCKET_NAME:-}}"
S3_ACCESS_KEY_ID="${S3_ACCESS_KEY_ID:-${YUANTUS_S3_ACCESS_KEY_ID:-}}"
S3_SECRET_ACCESS_KEY="${S3_SECRET_ACCESS_KEY:-${YUANTUS_S3_SECRET_ACCESS_KEY:-}}"
LOCAL_STORAGE_PATH="${LOCAL_STORAGE_PATH:-${YUANTUS_LOCAL_STORAGE_PATH:-}}"

CAD_ML_BASE_URL="${CAD_ML_BASE_URL:-${YUANTUS_CAD_ML_BASE_URL:-http://localhost:8001}}"
CAD_ML_HEALTH_URL="${CAD_ML_HEALTH_URL:-${CAD_ML_BASE_URL}/api/v1/vision/health}"
CAD_ML_TOKEN="${CAD_ML_SERVICE_TOKEN:-${YUANTUS_CAD_ML_SERVICE_TOKEN:-}}"

SAMPLE_FILE="${CAD_OCR_SAMPLE_FILE:-}"
ALLOW_EMPTY="${CAD_OCR_ALLOW_EMPTY:-0}"
TMP_SAMPLE=""

cleanup() {
  if [[ -n "$TMP_SAMPLE" && -f "$TMP_SAMPLE" ]]; then
    rm -f "$TMP_SAMPLE"
  fi
}
trap cleanup EXIT

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
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
  echo "SKIP: CAD ML Vision not available at $CAD_ML_HEALTH_URL (HTTP $HTTP_CODE)"
  exit 0
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
      ${STORAGE_TYPE:+YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"} \
      ${S3_ENDPOINT_URL:+YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"} \
      ${S3_PUBLIC_ENDPOINT_URL:+YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"} \
      ${S3_BUCKET_NAME:+YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"} \
      ${S3_ACCESS_KEY_ID:+YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"} \
      ${S3_SECRET_ACCESS_KEY:+YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"} \
      ${LOCAL_STORAGE_PATH:+YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

if [[ -z "$SAMPLE_FILE" ]]; then
  TMP_SAMPLE="$(mktemp -t yuantus_ocr_sample_XXXXXX)"
  TMP_SAMPLE="${TMP_SAMPLE}.png"
  export TMP_SAMPLE
  "$PY" - <<'PY'
import os
from PIL import Image, ImageDraw

path = os.environ["TMP_SAMPLE"]
img = Image.new("RGB", (900, 600), "white")
draw = ImageDraw.Draw(img)
lines = [
    "Drawing No: TEST-001",
    "Material: Steel",
    "Part Name: Sample Part",
]
y = 40
for line in lines:
    draw.text((40, y), line, fill="black")
    y += 40
img.save(path, format="PNG")
PY
  SAMPLE_FILE="$TMP_SAMPLE"
fi

if [[ ! -f "$SAMPLE_FILE" ]]; then
  fail "Sample file not found: $SAMPLE_FILE"
fi

echo "=============================================="
echo "CAD OCR Title Block Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "CAD_ML_BASE_URL: $CAD_ML_BASE_URL"
echo "SAMPLE: $SAMPLE_FILE"
echo "=============================================="

echo ""
echo "==> Seed identity/meta"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin --superuser >/dev/null
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Seeded identity/meta"

echo ""
echo "==> Login as admin"
API="$BASE_URL/api/v1"
ADMIN_TOKEN="$($CURL -X POST "$API/auth/login" \
  -H 'content-type: application/json' \
  -d "{\"tenant_id\":\"$TENANT\",\"username\":\"admin\",\"password\":\"admin\",\"org_id\":\"$ORG\"}" \
  | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [[ -z "$ADMIN_TOKEN" ]]; then
  fail "Admin login failed (no access_token)"
fi
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")
HEADERS=(-H "x-tenant-id: $TENANT" -H "x-org-id: $ORG")
ok "Admin login"

echo ""
echo "==> Upload image file"
IMPORT_RESP="$($CURL -X POST "$API/cad/import" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -F "file=@$SAMPLE_FILE;filename=$(basename "$SAMPLE_FILE")" \
  -F "create_extract_job=false" \
  -F "create_preview_job=false" \
  -F "create_geometry_job=false" \
  -F "create_dedup_job=false" \
  -F "create_ml_job=false")"
FILE_ID=$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')
if [[ -z "$FILE_ID" ]]; then
  echo "Response: $IMPORT_RESP" >&2
  fail "Failed to upload sample file"
fi
ok "Uploaded file: $FILE_ID"

echo ""
echo "==> Run cad_ml_vision job (direct)"
export FILE_ID TENANT ORG
export YUANTUS_CAD_ML_BASE_URL="$CAD_ML_BASE_URL"
if [[ -n "$CAD_ML_TOKEN" ]]; then
  export YUANTUS_CAD_ML_SERVICE_TOKEN="$CAD_ML_TOKEN"
else
  unset YUANTUS_CAD_ML_SERVICE_TOKEN
fi
if [[ -n "$DB_URL" ]]; then
  export YUANTUS_DATABASE_URL="$DB_URL"
fi
if [[ -n "$DB_URL_TEMPLATE" ]]; then
  export YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"
fi
if [[ -n "$IDENTITY_DB_URL" ]]; then
  export YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"
fi
if [[ -n "$STORAGE_TYPE" ]]; then
  export YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"
fi
if [[ -n "$S3_ENDPOINT_URL" ]]; then
  export YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"
fi
if [[ -n "$S3_PUBLIC_ENDPOINT_URL" ]]; then
  export YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"
fi
if [[ -n "$S3_BUCKET_NAME" ]]; then
  export YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"
fi
if [[ -n "$S3_ACCESS_KEY_ID" ]]; then
  export YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"
fi
if [[ -n "$S3_SECRET_ACCESS_KEY" ]]; then
  export YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"
fi
if [[ -n "$LOCAL_STORAGE_PATH" ]]; then
  export YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"
fi

VISION_RESULT="$("$PY" - <<'PY'
import json
import os

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_ml_vision

tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")
file_id = os.environ.get("FILE_ID")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()

with get_db_session() as session:
    result = cad_ml_vision({"file_id": file_id}, session)
print(json.dumps(result))
PY
)"
export VISION_RESULT
"$PY" - <<'PY'
import json
import os

raw = os.environ.get("VISION_RESULT", "")
data = json.loads(raw) if raw else {}
if not data.get("ok"):
    raise SystemExit("cad_ml_vision failed")
PY
ok "cad_ml_vision executed"

echo ""
echo "==> Fetch merged attributes"
ATTR_RESP="$($CURL -X GET "$API/cad/files/$FILE_ID/attributes" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"

export ATTR_RESP
FOUND_KEYS="$("$PY" - <<'PY'
import json
import os

raw = os.environ.get("ATTR_RESP", "")
data = json.loads(raw) if raw else {}
attrs = data.get("extracted_attributes") or {}
keys = [k for k in ("drawing_no", "material", "part_name", "revision", "weight") if attrs.get(k)]
print(",".join(keys))
PY
)"

if [[ -z "$FOUND_KEYS" ]]; then
  if [[ "$ALLOW_EMPTY" == "1" ]]; then
    ok "OCR attributes empty (allowed)"
    exit 0
  fi
  echo "Response: $ATTR_RESP" >&2
  fail "No OCR title-block attributes found"
fi

ok "Extracted OCR attributes: $FOUND_KEYS"
echo "ALL CHECKS PASSED"
