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
LOCAL_STORAGE_PATH="${LOCAL_STORAGE_PATH:-${YUANTUS_LOCAL_STORAGE_PATH:-./data/storage}}"

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

echo "=============================================="
echo "CAD Missing Source Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "LOCAL_STORAGE_PATH: $LOCAL_STORAGE_PATH"
echo "=============================================="

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
  FILE_ID="$FILE_ID" DB_URL="$DB_URL" "$PY" - <<'PY'
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

if [[ "$SYSTEM_PATH" = /* ]]; then
  FULL_PATH="$SYSTEM_PATH"
else
  FULL_PATH="$LOCAL_STORAGE_PATH/$SYSTEM_PATH"
fi

rm -f "$FULL_PATH"
ok "Deleted source file: $FULL_PATH"

echo ""
echo "==> Run worker once"
run_cli worker --worker-id cad-missing --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null || \
run_cli worker --worker-id cad-missing --poll-interval 1 --once >/dev/null
ok "Worker executed"

echo ""
echo "==> Verify job status"
JOB_STATUS="$(
  JOB_ID="$PREVIEW_JOB_ID" DB_URL="$DB_URL" "$PY" - <<'PY'
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
)"

if [[ -z "$JOB_STATUS" ]]; then
  fail "Could not fetch job status"
fi

STATUS="${JOB_STATUS%%|*}"
REST="${JOB_STATUS#*|}"
ATTEMPTS="${REST%%|*}"
LAST_ERROR="${REST#*|}"

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
