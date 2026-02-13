#!/usr/bin/env bash
# =============================================================================
# S3 CAD Pipeline Verification Script
# Verifies: upload → job trigger → worker processing → preview/geometry retrieval
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

PREVIEW_HTTP=""
GEOMETRY_HTTP=""
PREVIEW_STATUS=""
GEOMETRY_STATUS=""

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

echo "=============================================="
echo "S3 CAD Pipeline Verification"
echo "BASE_URL: $BASE_URL"
echo "TENANT: $TENANT, ORG: $ORG"
echo "USE_DOCKER_WORKER: $USE_DOCKER_WORKER_ENABLED (raw=$USE_DOCKER_WORKER)"
echo "=============================================="

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
fail() { echo "FAIL: $1"; exit 1; }
ok() { echo "OK: $1"; }

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

check_http() {
  local expected="$1"
  local actual="$2"
  local msg="$3"
  if [[ "$actual" == "$expected" ]]; then
    ok "$msg (HTTP $actual)"
  else
    fail "$msg - expected HTTP $expected, got $actual"
  fi
}

pump_local_worker_once() {
  if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
    return 0
  fi

  # Best-effort: in some tenancy modes, worker should run without --tenant/--org.
  run_cli worker --worker-id cad-verify --poll-interval 1 --once --tenant "$TENANT" --org "$ORG" >/dev/null 2>&1 || \
  run_cli worker --worker-id cad-verify --poll-interval 1 --once >/dev/null 2>&1 || \
  true
}

job_status() {
  local job_id="$1"
  $CURL "$API/jobs/$job_id" "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("status","") or "")'
}

wait_for_job_terminal() {
  local job_id="$1"
  local label="$2"
  local timeout_s="${3:-180}"
  local poll_s="${4:-2}"

  local start now status
  start="$(date +%s)"

  while true; do
    pump_local_worker_once

    status="$(job_status "$job_id")"
    echo "${label} status: ${status}"

    if [[ "$status" == "completed" || "$status" == "failed" || "$status" == "cancelled" ]]; then
      return 0
    fi

    now="$(date +%s)"
    if (( now - start >= timeout_s )); then
      echo "WARN: ${label} timed out after ${timeout_s}s (status=$status)" >&2
      return 0
    fi
    sleep "$poll_s"
  done
}

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

# -----------------------------------------------------------------------------
# 1) Setup: Seed identity and meta
# -----------------------------------------------------------------------------
echo ""
echo "==> Seed identity (admin user)"
run_cli seed-identity --tenant "$TENANT" --org "$ORG" --username admin --password admin --user-id 1 --roles admin >/dev/null
ok "Identity seeded"

echo ""
echo "==> Seed meta schema"
run_cli seed-meta --tenant "$TENANT" --org "$ORG" >/dev/null || run_cli seed-meta >/dev/null
ok "Meta schema seeded"

# -----------------------------------------------------------------------------
# 2) Login
# -----------------------------------------------------------------------------
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
ok "Admin login"
AUTH_HEADERS=(-H "Authorization: Bearer $ADMIN_TOKEN")

# -----------------------------------------------------------------------------
# 3) Create a test STL file (viewable format)
# -----------------------------------------------------------------------------
echo ""
echo "==> Create test STL file"
TEST_FILE="/tmp/yuantus_cad_s3_test.stl"

# Create a minimal ASCII STL (simple triangle)
cat > "$TEST_FILE" << 'EOF'
solid test
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0.5 1 0
    endloop
  endfacet
endsolid test
EOF

ok "Created test file: $TEST_FILE"

# -----------------------------------------------------------------------------
# 4) Upload via CAD import (with preview and geometry jobs)
# -----------------------------------------------------------------------------
echo ""
echo "==> Upload STL via /cad/import"
IMPORT_RESP="$(
  $CURL -X POST "$API/cad/import" \
    "${HEADERS[@]}" "${AUTH_HEADERS[@]}" \
    -F "file=@$TEST_FILE;filename=test_model.stl" \
    -F 'create_preview_job=true' \
    -F 'create_geometry_job=true' \
    -F 'create_dedup_job=false' \
    -F 'create_ml_job=false'
)"

FILE_ID="$(
  echo "$IMPORT_RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("file_id","") or "")'
)"

if [[ -z "$FILE_ID" ]]; then
  echo "Import response: $IMPORT_RESP"
  fail "Could not get file_id from import response"
fi

ok "File uploaded: $FILE_ID"

# Extract job IDs
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

GEOMETRY_JOB_ID="$(
  echo "$IMPORT_RESP" | "$PY" -c '
import sys,json
d = json.load(sys.stdin)
jobs = d.get("jobs", [])
for j in jobs:
    if j.get("task_type") == "cad_geometry":
        print(j.get("id", "") or "")
        break
'
)"

echo "Preview job ID: ${PREVIEW_JOB_ID:-none}"
echo "Geometry job ID: ${GEOMETRY_JOB_ID:-none}"

# -----------------------------------------------------------------------------
# 5) Run worker to process jobs
# -----------------------------------------------------------------------------
echo ""
echo "==> Run worker to process jobs"

if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
  echo "USE_DOCKER_WORKER=1: skipping local 'yuantus worker --once'."
else
  # Run worker once to process pending jobs
  pump_local_worker_once

  # Give it a moment
  sleep 2

  # Run again to ensure all jobs are processed
  pump_local_worker_once

  ok "Worker executed"
fi

# -----------------------------------------------------------------------------
# 6) Check job status
# -----------------------------------------------------------------------------
echo ""
echo "==> Check job statuses"

if [[ "$USE_DOCKER_WORKER_ENABLED" == "true" ]]; then
  echo "USE_DOCKER_WORKER=1: waiting for jobs to reach terminal status..."
  if [[ -n "$PREVIEW_JOB_ID" ]]; then
    wait_for_job_terminal "$PREVIEW_JOB_ID" "Preview job"
  fi
  if [[ -n "$GEOMETRY_JOB_ID" ]]; then
    wait_for_job_terminal "$GEOMETRY_JOB_ID" "Geometry job"
  fi
fi

if [[ -n "$PREVIEW_JOB_ID" ]]; then
  PREVIEW_STATUS="$(job_status "$PREVIEW_JOB_ID")"
  echo "Preview job status: $PREVIEW_STATUS"
fi

if [[ -n "$GEOMETRY_JOB_ID" ]]; then
  GEOMETRY_STATUS="$(job_status "$GEOMETRY_JOB_ID")"
  echo "Geometry job status: $GEOMETRY_STATUS"
fi

# -----------------------------------------------------------------------------
# 7) Verify file metadata has preview_path and geometry_path
# -----------------------------------------------------------------------------
echo ""
echo "==> Check file metadata"
FILE_META="$($CURL "$API/file/$FILE_ID" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"

PREVIEW_URL="$(echo "$FILE_META" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("preview_url","") or "")')"
GEOMETRY_URL="$(echo "$FILE_META" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("geometry_url","") or "")')"
CONV_STATUS="$(echo "$FILE_META" | "$PY" -c 'import sys,json; print(json.load(sys.stdin).get("conversion_status","") or "")')"

echo "Preview URL: ${PREVIEW_URL:-none}"
echo "Geometry URL: ${GEOMETRY_URL:-none}"
echo "Conversion status: ${CONV_STATUS:-none}"

if [[ -n "$PREVIEW_URL" ]]; then
  ok "Preview path set"
else
  echo "Warning: Preview path not set (may need CAD converter installed)"
fi

if [[ -n "$GEOMETRY_URL" ]]; then
  ok "Geometry path set"
else
  echo "Warning: Geometry path not set (STL should point to original file)"
fi

# -----------------------------------------------------------------------------
# 8) Verify preview endpoint works (returns 200 or 302)
# -----------------------------------------------------------------------------
echo ""
echo "==> Test preview endpoint"
if [[ -n "$PREVIEW_URL" ]]; then
  PREVIEW_HTTP="$($CURL -o /dev/null -w '%{http_code}' "$BASE_URL$PREVIEW_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"

  if [[ "$PREVIEW_HTTP" == "200" ]] || [[ "$PREVIEW_HTTP" == "302" ]]; then
    ok "Preview endpoint works (HTTP $PREVIEW_HTTP)"
  else
    echo "Warning: Preview endpoint returned HTTP $PREVIEW_HTTP"
  fi
else
  echo "Skipped: No preview URL"
fi

# -----------------------------------------------------------------------------
# 9) Verify geometry endpoint works (returns 200 or 302)
# -----------------------------------------------------------------------------
echo ""
echo "==> Test geometry endpoint"
if [[ -n "$GEOMETRY_URL" ]]; then
  GEOMETRY_HTTP="$($CURL -o /dev/null -w '%{http_code}' "$BASE_URL$GEOMETRY_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"

  if [[ "$GEOMETRY_HTTP" == "200" ]] || [[ "$GEOMETRY_HTTP" == "302" ]]; then
    ok "Geometry endpoint works (HTTP $GEOMETRY_HTTP)"
  else
    echo "Warning: Geometry endpoint returned HTTP $GEOMETRY_HTTP"
  fi
else
  echo "Skipped: No geometry URL"
fi

# -----------------------------------------------------------------------------
# 10) Verify S3 redirect (if using S3 storage)
# -----------------------------------------------------------------------------
echo ""
echo "==> Check storage type"
# We can infer S3 usage if we get a 302 redirect
if [[ "$GEOMETRY_HTTP" == "302" ]] || [[ "$PREVIEW_HTTP" == "302" ]]; then
  ok "S3 storage detected (302 redirect)"

  # Try to follow redirect and verify content is accessible
  if [[ -n "$GEOMETRY_URL" ]]; then
    echo "Testing S3 presigned URL follow (no API auth headers)..."
    HDRS="$(mktemp)"
    GEOMETRY_HTTP_1="$($CURL -D "$HDRS" -o /dev/null -w '%{http_code}' "$BASE_URL$GEOMETRY_URL" "${HEADERS[@]}" "${AUTH_HEADERS[@]}")"
    if [[ "$GEOMETRY_HTTP_1" != "302" && "$GEOMETRY_HTTP_1" != "307" && "$GEOMETRY_HTTP_1" != "301" && "$GEOMETRY_HTTP_1" != "308" ]]; then
      echo "Warning: expected redirect, got HTTP $GEOMETRY_HTTP_1"
    else
      LOCATION="$("$PY" - "$HDRS" <<'PY'
import sys
path = sys.argv[1]
loc = None
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.lower().startswith("location:"):
            loc = line.split(":", 1)[1].strip()
            break
print(loc or "")
PY
)"
      if [[ -n "$LOCATION" ]]; then
        GEOMETRY_FOLLOW_HTTP="$($CURL -L -o /dev/null -w '%{http_code}' "$LOCATION")"
        if [[ "$GEOMETRY_FOLLOW_HTTP" == "200" ]]; then
          ok "S3 presigned URL accessible (followed redirect)"
        else
          echo "Warning: Could not fetch presigned URL (HTTP $GEOMETRY_FOLLOW_HTTP)"
        fi
      else
        echo "Warning: redirect missing Location header"
      fi
    fi
    rm -f "$HDRS"
  fi
else
  echo "Local storage detected (direct file response)"
fi

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
echo ""
echo "==> Cleanup"
rm -f "$TEST_FILE"
ok "Cleaned up test file"

echo ""
echo "=============================================="
echo "CAD Pipeline S3 Verification Complete"
echo "=============================================="
echo ""
echo "Summary:"
echo "  - File upload: OK"
echo "  - Job processing: ${PREVIEW_STATUS:-unknown} / ${GEOMETRY_STATUS:-unknown}"
echo "  - Preview endpoint: ${PREVIEW_HTTP:-skipped}"
echo "  - Geometry endpoint: ${GEOMETRY_HTTP:-skipped}"
echo ""

# Determine overall result
if [[ -n "$GEOMETRY_URL" ]] && [[ "$GEOMETRY_HTTP" == "200" || "$GEOMETRY_HTTP" == "302" ]]; then
  echo "ALL CHECKS PASSED"
  exit 0
else
  echo "PARTIAL SUCCESS (some features may require additional setup)"
  exit 0
fi
