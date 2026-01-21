#!/usr/bin/env bash
# =============================================================================
# CAD 2D Preview Verification Script (DWG/DXF render)
# Requires CAD ML render service to be available.
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
CAD_PREVIEW_ALLOW_FALLBACK="${CAD_PREVIEW_ALLOW_FALLBACK:-0}"

SAMPLE_FILE="${CAD_PREVIEW_SAMPLE_FILE:-/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi
if [[ ! -f "$SAMPLE_FILE" ]]; then
  echo "SKIP: Sample file not found: $SAMPLE_FILE" >&2
  exit 0
fi

HTTP_CODE="$($CURL -o /dev/null -w '%{http_code}' "$CAD_ML_HEALTH_URL" 2>/dev/null || echo "000")"
if [[ "$HTTP_CODE" != "200" ]]; then
  if [[ "$CAD_PREVIEW_ALLOW_FALLBACK" == "1" ]]; then
    echo "WARN: CAD ML Vision not available at $CAD_ML_HEALTH_URL (HTTP $HTTP_CODE)"
    echo "      Continuing with fallback preview."
  else
    echo "SKIP: CAD ML Vision not available at $CAD_ML_HEALTH_URL (HTTP $HTTP_CODE)"
    exit 0
  fi
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

echo "=============================================="
echo "CAD 2D Preview Verification"
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
echo "==> Upload CAD file (DWG/DXF)"
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
echo "==> Run cad_preview job (direct)"
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

PREVIEW_RESULT="$("$PY" - <<'PY'
import json
import os

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_preview

tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")
file_id = os.environ.get("FILE_ID")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()

with get_db_session() as session:
    result = cad_preview({"file_id": file_id}, session)
print(json.dumps(result))
PY
)"
export PREVIEW_RESULT
"$PY" - <<'PY'
import json
import os

raw = os.environ.get("PREVIEW_RESULT", "")
data = json.loads(raw) if raw else {}
if not data.get("ok"):
    raise SystemExit("cad_preview failed")
PY
ok "cad_preview executed"

echo ""
echo "==> Check preview endpoint"
PREVIEW_CODE="$($CURL -o /dev/null -w '%{http_code}' \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" "${AUTH_HEADERS[@]}" \
  "$BASE_URL/api/v1/file/$FILE_ID/preview" 2>/dev/null || echo "000")"

if [[ "$PREVIEW_CODE" != "200" && "$PREVIEW_CODE" != "302" ]]; then
  fail "Preview endpoint returned HTTP $PREVIEW_CODE"
fi

ok "Preview endpoint HTTP $PREVIEW_CODE"

echo ""
echo "==> Update CAD properties"
PROPS_PAYLOAD='{"properties":{"part_number":"VERIFY-001","revision":"A"},"source":"verify"}'
PROPS_RESP="$($CURL -X PATCH "$API/cad/files/$FILE_ID/properties" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H "content-type: application/json" \
  -d "$PROPS_PAYLOAD")"
PROPS_SOURCE=$(echo "$PROPS_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("source",""))')
if [[ "$PROPS_SOURCE" != "verify" ]]; then
  echo "Response: $PROPS_RESP" >&2
  fail "CAD properties update failed"
fi
ok "CAD properties updated"

echo ""
echo "==> Update CAD view state"
DOC_PAYLOAD="$($CURL -sS \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" "${AUTH_HEADERS[@]}" \
  "$BASE_URL/api/v1/file/$FILE_ID/cad_document" 2>/dev/null || true)"
ENTITY_ID=$(DOC_PAYLOAD="$DOC_PAYLOAD" "$PY" - <<'PY'
import json
import os

raw = os.environ.get("DOC_PAYLOAD", "")
try:
    data = json.loads(raw)
except Exception:
    data = {}

entities = data.get("entities")
if isinstance(entities, list):
    for item in entities:
        if isinstance(item, dict):
            entity_id = item.get("id")
            if isinstance(entity_id, int):
                print(entity_id)
                break
PY
)
if [[ -n "$ENTITY_ID" ]]; then
  VIEW_PAYLOAD=$(cat <<JSON
{"hidden_entity_ids":[$ENTITY_ID],"notes":[{"entity_id":$ENTITY_ID,"note":"verify view note"}],"source":"verify","refresh_preview":false}
JSON
)
else
  VIEW_PAYLOAD='{"hidden_entity_ids":[],"notes":[],"source":"verify","refresh_preview":false}'
fi
VIEW_RESP="$($CURL -X PATCH "$API/cad/files/$FILE_ID/view-state" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H "content-type: application/json" \
  -d "$VIEW_PAYLOAD")"
VIEW_SOURCE=$(echo "$VIEW_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("source",""))')
if [[ "$VIEW_SOURCE" != "verify" ]]; then
  echo "Response: $VIEW_RESP" >&2
  fail "CAD view state update failed"
fi
ok "CAD view state updated"

echo ""
echo "==> Update CAD review"
REVIEW_RESP="$($CURL -X POST "$API/cad/files/$FILE_ID/review" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H "content-type: application/json" \
  -d '{"state":"approved","note":"verify review"}')"
REVIEW_STATE=$(echo "$REVIEW_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("state",""))')
if [[ "$REVIEW_STATE" != "approved" ]]; then
  echo "Response: $REVIEW_RESP" >&2
  fail "CAD review update failed"
fi
ok "CAD review updated"

echo ""
echo "==> Check CAD diff"
DIFF_RESP="$($CURL -sS \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  "$API/cad/files/$FILE_ID/diff?other_id=$FILE_ID")"
DIFF_SIZE=$(echo "$DIFF_RESP" | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("properties",{})))')
if [[ "$DIFF_SIZE" != "0" ]]; then
  echo "Response: $DIFF_RESP" >&2
  fail "CAD diff expected empty properties"
fi
ok "CAD diff ok"

echo ""
echo "==> Check CAD history"
HISTORY_RESP="$($CURL -sS \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  "$API/cad/files/$FILE_ID/history")"
HISTORY_ACTIONS=$(echo "$HISTORY_RESP" | "$PY" -c 'import sys,json;print("|".join([e.get("action","") for e in json.load(sys.stdin).get("entries",[])]))')
if [[ "$HISTORY_ACTIONS" != *"cad_properties_update"* ]]; then
  echo "Response: $HISTORY_RESP" >&2
  fail "CAD history missing properties update"
fi
if [[ "$HISTORY_ACTIONS" != *"cad_view_state_update"* ]]; then
  echo "Response: $HISTORY_RESP" >&2
  fail "CAD history missing view state update"
fi
if [[ "$HISTORY_ACTIONS" != *"cad_review_update"* ]]; then
  echo "Response: $HISTORY_RESP" >&2
  fail "CAD history missing review update"
fi
ok "CAD history ok"

echo ""
echo "==> Check CAD mesh stats (optional)"
MESH_TMP="$(mktemp)"
MESH_CODE="$($CURL -o "$MESH_TMP" -w '%{http_code}' \
  -H "x-tenant-id: $TENANT" -H "x-org-id: $ORG" "${AUTH_HEADERS[@]}" \
  "$API/cad/files/$FILE_ID/mesh-stats" 2>/dev/null || echo "000")"
if [[ "$MESH_CODE" == "200" ]]; then
  read -r MESH_AVAILABLE MESH_KEYS <<<"$("$PY" - "$MESH_TMP" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
stats = data.get("stats") or {}
available = stats.get("available")
if available is None:
    available = True
print(str(bool(available)).lower())
print(len(stats))
PY
)"
  if [[ "$MESH_AVAILABLE" != "true" ]]; then
    echo "SKIP: mesh stats unavailable (available=false)"
  else
    if [[ "$MESH_KEYS" == "0" ]]; then
      rm -f "$MESH_TMP"
      fail "CAD mesh stats empty"
    fi
    ok "CAD mesh stats ok"
  fi
else
  echo "SKIP: mesh stats unavailable (HTTP $MESH_CODE)"
fi
rm -f "$MESH_TMP"
echo "ALL CHECKS PASSED"
