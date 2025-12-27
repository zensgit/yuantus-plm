#!/usr/bin/env bash
# =============================================================================
# CAD Extractor External Verification Script
# Verifies external cad_extractor integration using a real extractor service.
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

EXTRACTOR_URL="${CAD_EXTRACTOR_BASE_URL:-${YUANTUS_CAD_EXTRACTOR_BASE_URL:-}}"
EXTRACTOR_TOKEN="${CAD_EXTRACTOR_SERVICE_TOKEN:-${YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN:-}}"
SAMPLE_FILE="${CAD_EXTRACTOR_SAMPLE_FILE:-}"
UPLOAD_NAME="${CAD_EXTRACTOR_UPLOAD_NAME:-}"
EXPECT_KEY="${CAD_EXTRACTOR_EXPECT_KEY:-}"
EXPECT_VALUE="${CAD_EXTRACTOR_EXPECT_VALUE:-}"
ALLOW_EMPTY="${CAD_EXTRACTOR_ALLOW_EMPTY:-0}"
OVERRIDE_FORMAT="${CAD_EXTRACTOR_CAD_FORMAT:-}"
OVERRIDE_CONNECTOR="${CAD_EXTRACTOR_CONNECTOR_ID:-}"

if [[ ! -x "$CLI" ]]; then
  echo "Missing CLI at $CLI (set CLI=...)" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi
if [[ -z "$EXTRACTOR_URL" ]]; then
  echo "Missing CAD_EXTRACTOR_BASE_URL (set CAD_EXTRACTOR_BASE_URL=...)" >&2
  exit 2
fi
if [[ -z "$SAMPLE_FILE" || ! -f "$SAMPLE_FILE" ]]; then
  echo "Missing CAD_EXTRACTOR_SAMPLE_FILE or file not found" >&2
  exit 2
fi
if [[ -z "$DB_URL" ]]; then
  DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus"
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
FILENAME="${UPLOAD_NAME:-$(basename "$SAMPLE_FILE")}"

EXTRA_FORMS=()
if [[ -n "$OVERRIDE_FORMAT" ]]; then
  EXTRA_FORMS+=( -F "cad_format=$OVERRIDE_FORMAT" )
fi
if [[ -n "$OVERRIDE_CONNECTOR" ]]; then
  EXTRA_FORMS+=( -F "cad_connector_id=$OVERRIDE_CONNECTOR" )
fi


echo "=============================================="
echo "CAD Extractor External Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "EXTRACTOR: $EXTRACTOR_URL"
echo "SAMPLE: $SAMPLE_FILE"
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
echo "==> Upload CAD file and enqueue extract job"
IMPORT_RESP="$($CURL -X POST "$API/cad/import" \
  "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
  -F "file=@$SAMPLE_FILE;filename=$FILENAME" \
  -F "create_extract_job=true" \
  -F "create_preview_job=false" \
  -F "create_geometry_job=false" \
  -F "create_dedup_job=false" \
  -F "create_ml_job=false" \
  "${EXTRA_FORMS[@]}")"
FILE_ID=$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;print(json.load(sys.stdin).get("file_id",""))')
JOB_ID=$(echo "$IMPORT_RESP" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);print(next((j.get("id") for j in d.get("jobs",[]) if j.get("task_type")=="cad_extract"), ""))')
if [[ -z "$FILE_ID" || -z "$JOB_ID" ]]; then
  echo "Response: $IMPORT_RESP" >&2
  fail "Failed to enqueue cad_extract job"
fi
ok "Uploaded file: $FILE_ID"
ok "Created job: $JOB_ID"

echo ""
echo "==> Process cad_extract job (direct)"
export JOB_ID="$JOB_ID"
export TENANT="$TENANT"
export ORG="$ORG"
export YUANTUS_CAD_EXTRACTOR_BASE_URL="$EXTRACTOR_URL"
export YUANTUS_CAD_EXTRACTOR_MODE="required"
export YUANTUS_DATABASE_URL="$DB_URL"
if [[ -n "$DB_URL_TEMPLATE" ]]; then
  export YUANTUS_DATABASE_URL_TEMPLATE="$DB_URL_TEMPLATE"
fi
if [[ -n "$EXTRACTOR_TOKEN" ]]; then
  export YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN="$EXTRACTOR_TOKEN"
else
  unset YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN
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

"$PY" - <<'PY'
import os
from datetime import datetime

from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract

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
    job.worker_id = "cad-extractor-external"
    job.started_at = datetime.utcnow()
    job.attempt_count = (job.attempt_count or 0) + 1
    session.add(job)
    session.commit()

    try:
        result = cad_extract(job.payload, session)
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
ok "Job completed"

echo ""
echo "==> Verify extracted attributes source=external"
ATTR_JSON="$($CURL "$API/cad/files/$FILE_ID/attributes" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
VERIFY=$(RESP_JSON="$ATTR_JSON" EXPECT_KEY="$EXPECT_KEY" EXPECT_VALUE="$EXPECT_VALUE" ALLOW_EMPTY="$ALLOW_EMPTY" "$PY" - <<'PY'
import os, json
resp = json.loads(os.environ.get("RESP_JSON", ""))
if resp.get("source") != "external":
    print("FAIL:source")
    raise SystemExit(0)
attrs = resp.get("extracted_attributes") or {}
if os.environ.get("ALLOW_EMPTY") != "1" and len(attrs) == 0:
    print("FAIL:empty")
    raise SystemExit(0)
key = os.environ.get("EXPECT_KEY") or ""
if key:
    if key not in attrs:
        print("FAIL:missing_key")
        raise SystemExit(0)
    expect_val = os.environ.get("EXPECT_VALUE")
    if expect_val and str(attrs.get(key)) != str(expect_val):
        print("FAIL:value_mismatch")
        raise SystemExit(0)
print("OK")
PY
)
if [[ "$VERIFY" != "OK" ]]; then
  echo "Response: $ATTR_JSON" >&2
  fail "External extractor verification failed"
fi
ok "External extractor verified"

echo ""
echo "=============================================="
echo "CAD Extractor External Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
