#!/usr/bin/env bash
# =============================================================================
# CAD Attribute Sync Verification Script
# Verifies x-cad-synced mapping from CAD extracted attributes to Item properties.
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
STORAGE_TYPE="${STORAGE_TYPE:-${YUANTUS_STORAGE_TYPE:-}}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-${YUANTUS_S3_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}}"
S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${YUANTUS_S3_BUCKET_NAME:-}}"
S3_ACCESS_KEY_ID="${S3_ACCESS_KEY_ID:-${YUANTUS_S3_ACCESS_KEY_ID:-}}"
S3_SECRET_ACCESS_KEY="${S3_SECRET_ACCESS_KEY:-${YUANTUS_S3_SECRET_ACCESS_KEY:-}}"
LOCAL_STORAGE_PATH="${LOCAL_STORAGE_PATH:-${YUANTUS_LOCAL_STORAGE_PATH:-}}"
SAMPLE_FILE="${CAD_SYNC_SAMPLE_FILE:-}"
EXPECTED_ITEM_NUMBER="${CAD_SYNC_EXPECT_ITEM_NUMBER:-HC-001}"
EXPECTED_DESCRIPTION="${CAD_SYNC_EXPECT_DESCRIPTION:-浩辰CAD零件}"
EXPECTED_REVISION="${CAD_SYNC_EXPECT_REVISION:-}"
CAD_FORMAT_OVERRIDE="${CAD_SYNC_CAD_FORMAT:-}"
CAD_CONNECTOR_OVERRIDE="${CAD_SYNC_CONNECTOR_ID:-}"

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

TS="$(date +%s)"

echo "=============================================="
echo "CAD Attribute Sync Verification"
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

echo ""
echo "==> Fetch Part ItemType properties"
ITEMTYPE_JSON="$($CURL "$API/meta/item-types/Part" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
ITEM_NUMBER_PROP_ID="$(echo "$ITEMTYPE_JSON" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);props=d.get("properties",[]);print(next((p["id"] for p in props if p.get("name")=="item_number"), ""))')"
DESC_PROP_ID="$(echo "$ITEMTYPE_JSON" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);props=d.get("properties",[]);print(next((p["id"] for p in props if p.get("name")=="description"), ""))')"
REV_PROP_ID="$(echo "$ITEMTYPE_JSON" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);props=d.get("properties",[]);print(next((p["id"] for p in props if p.get("name")=="revision"), ""))')"
if [[ -z "$ITEM_NUMBER_PROP_ID" || -z "$DESC_PROP_ID" ]]; then
  fail "Missing item_number or description property on Part"
fi
if [[ -n "$EXPECTED_REVISION" && -z "$REV_PROP_ID" ]]; then
  fail "Missing revision property on Part (needed for CAD_SYNC_EXPECT_REVISION)"
fi
ok "Resolved property IDs"

echo ""
echo "==> Configure CAD sync mapping"
# item_number maps from CAD attribute part_number
$CURL -X PATCH "$API/meta/item-types/Part/properties/$ITEM_NUMBER_PROP_ID" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H 'content-type: application/json' \
  -d '{"is_cad_synced":true,"ui_options":{"cad_key":"part_number"}}' \
  | "$PY" -c 'import sys,json;json.load(sys.stdin);print("item_number updated")' >/dev/null
# description uses default mapping (same key)
$CURL -X PATCH "$API/meta/item-types/Part/properties/$DESC_PROP_ID" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -H 'content-type: application/json' \
  -d '{"is_cad_synced":true}' \
  | "$PY" -c 'import sys,json;json.load(sys.stdin);print("description updated")' >/dev/null
if [[ -n "$EXPECTED_REVISION" ]]; then
  $CURL -X PATCH "$API/meta/item-types/Part/properties/$REV_PROP_ID" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -H 'content-type: application/json' \
    -d '{"is_cad_synced":true,"ui_options":{"cad_key":"revision"}}' \
    | "$PY" -c 'import sys,json;json.load(sys.stdin);print("revision updated")' >/dev/null
fi
ok "CAD sync mapping configured"

echo ""
echo "==> Create Part item"
ITEM_NUMBER="SYNC-$TS"
EXPECTED_NAME="Cad Sync Test $TS"
ITEM_ID="$(
  $CURL -X POST "$API/aml/apply" \
    -H 'content-type: application/json' \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"$ITEM_NUMBER\",\"name\":\"$EXPECTED_NAME\",\"description\":\"Original\"}}" \
    | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("id",""))'
)"
if [[ -z "$ITEM_ID" ]]; then
  fail "Failed to create Part item"
fi
ok "Created Part: $ITEM_ID"

echo ""
echo "==> Upload CAD file and enqueue extract job"
cleanup_file=0
if [[ -z "$SAMPLE_FILE" ]]; then
  DWG_FILE="/tmp/yuantus_haochencad_sync_$TS.dwg"
  cat > "$DWG_FILE" <<EOF
# run_id=$TS
图号=HC-001
名称=浩辰CAD零件
版本=A
材料=钢
EOF
  cleanup_file=1
else
  DWG_FILE="$SAMPLE_FILE"
fi
if [[ -z "$CAD_FORMAT_OVERRIDE" && -z "$SAMPLE_FILE" ]]; then
  CAD_FORMAT_OVERRIDE="HAOCHEN"
fi
FILENAME="$(basename "$DWG_FILE")"
EXTRA_FORMS=()
if [[ -n "$CAD_FORMAT_OVERRIDE" ]]; then
  EXTRA_FORMS+=( -F "cad_format=$CAD_FORMAT_OVERRIDE" )
fi
if [[ -n "$CAD_CONNECTOR_OVERRIDE" ]]; then
  EXTRA_FORMS+=( -F "cad_connector_id=$CAD_CONNECTOR_OVERRIDE" )
fi

IMPORT_RESP="$(
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$DWG_FILE;filename=$FILENAME" \
    -F "item_id=$ITEM_ID" \
    -F "create_extract_job=true" \
    -F "create_preview_job=false" \
    -F "create_geometry_job=false" \
    -F "create_dedup_job=false" \
    -F "create_ml_job=false" \
    "${EXTRA_FORMS[@]}"
)"
FILE_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')"
JOB_ID="$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);print(next((j.get("id") for j in d.get("jobs",[]) if j.get("task_type")=="cad_extract"), ""))')"
if [[ -z "$FILE_ID" || -z "$JOB_ID" ]]; then
  echo "Response: $IMPORT_RESP"
  fail "Failed to enqueue cad_extract job"
fi
ok "Uploaded file: $FILE_ID"
ok "Created job: $JOB_ID"

echo ""
echo "==> Run worker and wait for job completion"
completed=0
for i in {1..5}; do
  run_cli worker --worker-id cad-sync --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
  run_cli worker --worker-id cad-sync --poll-interval 1 --once >/dev/null
  STATUS="$($CURL "$API/jobs/$JOB_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
  if [[ "$STATUS" == "completed" ]]; then
    ok "Job completed"
    completed=1
    break
  fi
  sleep 1
done

if [[ "$completed" -ne 1 ]]; then
  echo "Worker did not complete job (status=$STATUS). Running direct processor..."
  JOB_ID="$JOB_ID" TENANT="$TENANT" ORG="$ORG" \
  ${DB_URL:+YUANTUS_DATABASE_URL="$DB_URL"} \
  ${IDENTITY_DB_URL:+YUANTUS_IDENTITY_DATABASE_URL="$IDENTITY_DB_URL"} \
  ${STORAGE_TYPE:+YUANTUS_STORAGE_TYPE="$STORAGE_TYPE"} \
  ${S3_ENDPOINT_URL:+YUANTUS_S3_ENDPOINT_URL="$S3_ENDPOINT_URL"} \
  ${S3_PUBLIC_ENDPOINT_URL:+YUANTUS_S3_PUBLIC_ENDPOINT_URL="$S3_PUBLIC_ENDPOINT_URL"} \
  ${S3_BUCKET_NAME:+YUANTUS_S3_BUCKET_NAME="$S3_BUCKET_NAME"} \
  ${S3_ACCESS_KEY_ID:+YUANTUS_S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"} \
  ${S3_SECRET_ACCESS_KEY:+YUANTUS_S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"} \
  ${LOCAL_STORAGE_PATH:+YUANTUS_LOCAL_STORAGE_PATH="$LOCAL_STORAGE_PATH"} \
  "$PY" - <<'PY'
import os
from datetime import datetime

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract
from yuantus.meta_engine.services.cad_service import CadService

job_id = os.environ.get("JOB_ID")
tenant = os.environ.get("TENANT")
org = os.environ.get("ORG")

if not job_id or not tenant or not org:
    raise SystemExit("Missing JOB_ID/TENANT/ORG for direct processor")

tenant_id_var.set(tenant)
org_id_var.set(org)
import_all_models()

with get_db_session() as session:
    svc = JobService(session)
    job = svc.get_job(job_id)
    if not job:
        raise SystemExit("Job not found")
    job.status = "processing"
    job.worker_id = "cad-sync-direct"
    job.started_at = datetime.utcnow()
    job.attempt_count = (job.attempt_count or 0) + 1
    session.add(job)
    session.commit()

    try:
        result = cad_extract(job.payload, session)
        if isinstance(result, dict) and result.get("extracted_attributes"):
            item_id = job.payload.get("item_id")
            if item_id:
                cad_service = CadService(session)
                cad_service.sync_attributes_to_item(
                    item_id=item_id,
                    extracted_attributes=result.get("extracted_attributes") or {},
                    user_id=job.created_by_id or 1,
                )
        svc.complete_job(job.id, result=result)
    except JobFatalError as exc:
        svc.fail_job(job.id, str(exc), retry=False)
    except Exception as exc:
        svc.fail_job(job.id, str(exc))
PY

  STATUS="$($CURL "$API/jobs/$JOB_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))')"
  if [[ "$STATUS" != "completed" ]]; then
    fail "Job did not complete (status=$STATUS)"
  fi
  ok "Job completed (direct processor)"
fi

echo ""
echo "==> Verify CAD-synced properties"
ITEM_JSON="$($CURL -X POST "$API/aml/apply" \
  -H 'content-type: application/json' \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -d "{\"type\":\"Part\",\"action\":\"get\",\"id\":\"$ITEM_ID\"}")"
RESP_JSON="$ITEM_JSON" EXPECTED_NAME="$EXPECTED_NAME" EXPECTED_ITEM_NUMBER="$EXPECTED_ITEM_NUMBER" EXPECTED_DESCRIPTION="$EXPECTED_DESCRIPTION" EXPECTED_REVISION="$EXPECTED_REVISION" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "{}")
data = json.loads(raw)
items = data.get("items") or []
if not items:
    raise SystemExit("No items returned")
props = items[0].get("properties") or {}
expected_item = os.environ.get("EXPECTED_ITEM_NUMBER", "")
expected_desc = os.environ.get("EXPECTED_DESCRIPTION", "")
expected_rev = os.environ.get("EXPECTED_REVISION", "")
if expected_item and props.get("item_number") != expected_item:
    raise SystemExit(f"item_number not synced: {props.get('item_number')}")
if expected_desc and props.get("description") != expected_desc:
    raise SystemExit(f"description not synced: {props.get('description')}")
if expected_rev and props.get("revision") != expected_rev:
    raise SystemExit(f"revision not synced: {props.get('revision')}")
if props.get("name") != os.environ.get("EXPECTED_NAME", ""):
    raise SystemExit(f"name should remain unchanged: {props.get('name')}")
if "material" in props:
    raise SystemExit("material should not be synced")
print("CAD sync mapping verified")
PY
ok "CAD sync mapping verified"

echo ""
echo "==> Verify cad_extract attributes endpoint"
ATTR_RESP="$($CURL "$API/cad/files/$FILE_ID/attributes" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
RESP_JSON="$ATTR_RESP" EXPECTED_ITEM_NUMBER="$EXPECTED_ITEM_NUMBER" EXPECTED_DESCRIPTION="$EXPECTED_DESCRIPTION" EXPECTED_REVISION="$EXPECTED_REVISION" "$PY" - <<'PY'
import os, json
raw = os.environ.get("RESP_JSON", "{}")
data = json.loads(raw)
attrs = data.get("extracted_attributes") or {}
expected_item = os.environ.get("EXPECTED_ITEM_NUMBER", "")
expected_desc = os.environ.get("EXPECTED_DESCRIPTION", "")
expected_rev = os.environ.get("EXPECTED_REVISION", "")
if expected_item and attrs.get("part_number") != expected_item:
    raise SystemExit(f"cad_extract part_number mismatch: {attrs.get('part_number')}")
if expected_desc and attrs.get("description") != expected_desc:
    raise SystemExit(f"cad_extract description mismatch: {attrs.get('description')}")
if expected_rev and attrs.get("revision") != expected_rev:
    raise SystemExit(f"cad_extract revision mismatch: {attrs.get('revision')}")
if data.get("job_status") != "completed":
    raise SystemExit(f"cad_extract job_status mismatch: {data.get('job_status')}")
print("cad_extract attributes verified")
PY
ok "cad_extract attributes verified"

echo ""
echo "==> Cleanup"
if [[ "$cleanup_file" -eq 1 ]]; then
  rm -f "$DWG_FILE"
  ok "Cleaned up temp file"
else
  ok "Skipped cleanup for CAD_SYNC_SAMPLE_FILE"
fi

echo ""
echo "=============================================="
echo "CAD Attribute Sync Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
