#!/usr/bin/env bash
# =============================================================================
# CAD Missing Source Verification Script
# Ensures missing source files cause a non-retryable job failure.
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
TENANCY_MODE_ENV="${TENANCY_MODE_ENV:-${YUANTUS_TENANCY_MODE:-}}"
STORAGE_TYPE="${STORAGE_TYPE:-${YUANTUS_STORAGE_TYPE:-}}"
S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-${YUANTUS_S3_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}}"
S3_PUBLIC_ENDPOINT_URL="${S3_PUBLIC_ENDPOINT_URL:-${YUANTUS_S3_PUBLIC_ENDPOINT_URL:-}}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-${YUANTUS_S3_BUCKET_NAME:-}}"
S3_ACCESS_KEY_ID="${S3_ACCESS_KEY_ID:-${YUANTUS_S3_ACCESS_KEY_ID:-}}"
S3_SECRET_ACCESS_KEY="${S3_SECRET_ACCESS_KEY:-${YUANTUS_S3_SECRET_ACCESS_KEY:-}}"
LOCAL_STORAGE_PATH="${LOCAL_STORAGE_PATH:-${YUANTUS_LOCAL_STORAGE_PATH:-./data/storage}}"
USE_DOCKER_WORKER="${USE_DOCKER_WORKER:-0}"

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

fail() { echo "FAIL: $1" >&2; exit 1; }
ok() { echo "OK: $1"; }

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|y|Y|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

USE_DOCKER_WORKER_ENABLED=false
if is_truthy "$USE_DOCKER_WORKER"; then
  USE_DOCKER_WORKER_ENABLED=true
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
      ${TENANCY_MODE_ENV:+YUANTUS_TENANCY_MODE="$TENANCY_MODE_ENV"} \
      ${identity_url:+YUANTUS_IDENTITY_DATABASE_URL="$identity_url"} \
      "$CLI" "$@"
  else
    "$CLI" "$@"
  fi
}

pump_local_worker_once() {
  if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
    return 0
  fi

  run_cli worker --worker-id cad-missing --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null 2>&1 || \
  run_cli worker --worker-id cad-missing --poll-interval 1 --once >/dev/null 2>&1 || \
  true
}

query_job_status() {
  JOB_ID="$PREVIEW_JOB_ID" DB_URL="$DB_URL_EFFECTIVE" "$PY" - <<'PY'
import os
from sqlalchemy import create_engine, text

job_id = os.environ.get("JOB_ID")
db_url = os.environ.get("DB_URL")
if not db_url:
    raise SystemExit("")
engine = create_engine(db_url)
with engine.begin() as conn:
    row = conn.execute(
        text("SELECT status, attempt_count, last_error FROM meta_conversion_jobs WHERE id=:jid"),
        {"jid": job_id},
    ).fetchone()
    if not row:
        print("")
    else:
        status, attempts, last_error = row
        print(f"{status}|{attempts}|{last_error or ''}")
PY
}

echo "=============================================="
echo "CAD Missing Source Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "LOCAL_STORAGE_PATH: $LOCAL_STORAGE_PATH"
echo "USE_DOCKER_WORKER: $USE_DOCKER_WORKER_ENABLED (raw=$USE_DOCKER_WORKER)"
echo "=============================================="

if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
  echo ""
  echo "==> Preflight: Docker worker container (best-effort)"
  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' --filter 'label=com.docker.compose.service=worker' --filter 'status=running' | grep -q .; then
      ok "Docker worker container is running"
    else
      echo "WARN: USE_DOCKER_WORKER=1 but no running compose worker container found (label com.docker.compose.service=worker)." >&2
      echo "WARN: The script will wait for jobs to be processed by an external worker; start the worker if it times out." >&2
    fi
  else
    echo "WARN: docker not found; USE_DOCKER_WORKER=1 will just wait for jobs to be processed by an external worker." >&2
  fi
fi

echo ""
echo "==> Seed identity (admin user)"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
ok "Identity seeded"

echo ""
echo "==> Seed meta schema"
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Meta schema seeded"

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

TENANCY_MODE_HEALTH="$(
  $CURL "$API/health" \
    | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("tenancy_mode",""))' 2>/dev/null || echo ""
)"
if [[ -z "$TENANCY_MODE_ENV" && -n "$TENANCY_MODE_HEALTH" ]]; then
  TENANCY_MODE_ENV="$TENANCY_MODE_HEALTH"
fi

DB_URL_EFFECTIVE="$DB_URL"
if [[ -n "$DB_URL_TEMPLATE" ]]; then
  if [[ "$TENANCY_MODE_ENV" == "db-per-tenant-org" ]]; then
    DB_URL_EFFECTIVE="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
    DB_URL_EFFECTIVE="${DB_URL_EFFECTIVE//\{org_id\}/$ORG}"
  elif [[ "$TENANCY_MODE_ENV" == "db-per-tenant" ]]; then
    DB_URL_EFFECTIVE="${DB_URL_TEMPLATE//\{tenant_id\}/$TENANT}"
  fi
fi

if [[ -z "$DB_URL_EFFECTIVE" ]]; then
  fail "Missing DB_URL/DB_URL_TEMPLATE for direct DB query"
fi

echo ""
echo "==> Create test CAD file"
TEST_FILE="/tmp/yuantus_missing_source_test.dwg"
cat > "$TEST_FILE" << 'EOF'
Yuantus Missing Source Test
EOF
ok "Created test file: $TEST_FILE"

echo ""
echo "==> Upload via /cad/import (preview job)"
IMPORT_RESP="$(
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$TEST_FILE;filename=missing_source.dwg" \
    -F 'create_preview_job=true' \
    -F 'create_geometry_job=false' \
    -F 'create_dedup_job=false' \
    -F 'create_ml_job=false'
)"

FILE_ID="$(
  echo "$IMPORT_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("file_id","") or "")'
)"
PREVIEW_JOB_ID="$(
  echo "$IMPORT_RESP" | "$PY" -c '
import sys,json
d = json.load(sys.stdin)
jobs = d.get("jobs", [])
for j in jobs:
    if j.get("task_type") == "cad_preview":
        print(j.get("id", "") or "")
        break
'
)"

if [[ -z "$FILE_ID" || -z "$PREVIEW_JOB_ID" ]]; then
  echo "Import response: $IMPORT_RESP"
  fail "Missing file_id or preview job id"
fi
ok "Created file/job: $FILE_ID / $PREVIEW_JOB_ID"

echo ""
echo "==> Remove source file from local storage"
SYSTEM_PATH="$(
  FILE_ID="$FILE_ID" DB_URL="$DB_URL_EFFECTIVE" "$PY" - <<'PY'
import os
from sqlalchemy import create_engine, text

file_id = os.environ.get("FILE_ID")
db_url = os.environ.get("DB_URL")
if not db_url:
    raise SystemExit("")
engine = create_engine(db_url)
with engine.begin() as conn:
    row = conn.execute(
        text("SELECT system_path FROM meta_files WHERE id=:fid"),
        {"fid": file_id},
    ).fetchone()
    if not row:
        print("")
    else:
        print(row[0] or "")
PY
)"

if [[ -z "$SYSTEM_PATH" ]]; then
  fail "Could not resolve system_path for file"
fi

storage_mode="${STORAGE_TYPE,,}"
if [[ "$storage_mode" == "s3" ]]; then
  if [[ -z "$S3_BUCKET_NAME" || -z "$S3_ENDPOINT_URL" || -z "$S3_ACCESS_KEY_ID" || -z "$S3_SECRET_ACCESS_KEY" ]]; then
    fail "Missing S3 settings for deletion (S3_BUCKET_NAME/S3_ENDPOINT_URL/S3_ACCESS_KEY_ID/S3_SECRET_ACCESS_KEY)"
  fi
  SYSTEM_PATH="$SYSTEM_PATH" \
  S3_BUCKET_NAME="$S3_BUCKET_NAME" \
  S3_ENDPOINT_URL="$S3_ENDPOINT_URL" \
  S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID" \
  S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY" \
  "$PY" - <<'PY'
import os

import boto3

key = os.environ.get("SYSTEM_PATH")
bucket = os.environ.get("S3_BUCKET_NAME")
endpoint = os.environ.get("S3_ENDPOINT_URL")
access_key = os.environ.get("S3_ACCESS_KEY_ID")
secret_key = os.environ.get("S3_SECRET_ACCESS_KEY")

if not (key and bucket and endpoint and access_key and secret_key):
    raise SystemExit("Missing S3 settings or system path")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
)
s3.delete_object(Bucket=bucket, Key=key)
PY
  ok "Deleted source object: s3://$S3_BUCKET_NAME/$SYSTEM_PATH"
else
  if [[ "$SYSTEM_PATH" = /* ]]; then
    FULL_PATH="$SYSTEM_PATH"
  else
    FULL_PATH="$LOCAL_STORAGE_PATH/$SYSTEM_PATH"
  fi
  rm -f "$FULL_PATH"
  ok "Deleted source file: $FULL_PATH"
fi

echo ""
echo "==> Wait for job failure (missing source)"
STATUS=""
ATTEMPTS=""
LAST_ERROR=""
JOB_STATUS=""
start="$(date +%s)"
while true; do
  pump_local_worker_once

  JOB_STATUS="$(query_job_status || true)"
  if [[ -n "$JOB_STATUS" ]]; then
    STATUS="${JOB_STATUS%%|*}"
    REST="${JOB_STATUS#*|}"
    ATTEMPTS="${REST%%|*}"
    LAST_ERROR="${REST#*|}"
    echo "Job status: $STATUS (attempt_count=$ATTEMPTS)"
    if [[ "$STATUS" == "failed" || "$STATUS" == "completed" || "$STATUS" == "cancelled" ]]; then
      break
    fi
  fi

  now="$(date +%s)"
  if (( now - start >= 240 )); then
    fail "Timed out waiting for job terminal status (last_status=${STATUS:-unknown})"
  fi
  sleep 2
done

if [[ -z "$JOB_STATUS" ]]; then
  fail "Could not fetch job status"
fi

if [[ "$STATUS" != "failed" ]]; then
  fail "Expected status=failed, got $STATUS"
fi
if [[ "$ATTEMPTS" -gt 1 ]]; then
  fail "Expected no retries (attempt_count=1), got $ATTEMPTS"
fi
if [[ "$LAST_ERROR" != *"Source file missing"* ]]; then
  fail "Expected missing source error, got: $LAST_ERROR"
fi
ok "Job failed without retries"

echo ""
echo "=============================================="
echo "CAD Missing Source Verification Complete"
echo "=============================================="
echo "ALL CHECKS PASSED"
