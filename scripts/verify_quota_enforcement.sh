#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Quota enforcement.
#
# Coverage:
# - admin quota get/update (superuser-only): /api/v1/admin/quota
# - enforcement on file upload (429 QUOTA_EXCEEDED) when max_files is reached
# - RBAC guardrail: a non-superuser user gets 403 on /api/v1/admin/quota
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-quota-enforcement/${timestamp}"
OUT_DIR="${OUT_DIR:-$OUT_DIR_DEFAULT}"
mkdir -p "$OUT_DIR"

log() { echo "[$(date +%H:%M:%S)] $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

PY_BIN="${PY_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="python3"
fi

YUANTUS_BIN="${YUANTUS_BIN:-${REPO_ROOT}/.venv/bin/yuantus}"
if [[ ! -x "$YUANTUS_BIN" ]]; then
  YUANTUS_BIN="yuantus"
fi

UVICORN_BIN="${UVICORN_BIN:-${REPO_ROOT}/.venv/bin/uvicorn}"
if [[ ! -x "$UVICORN_BIN" ]]; then
  UVICORN_BIN="uvicorn"
fi

PORT="${PORT:-0}"
if [[ "$PORT" == "0" ]]; then
  PORT="$("$PY_BIN" - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT}}"

TENANT_ID="${TENANT_ID:-tenant-1}"
ORG_ID="${ORG_ID:-org-1}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"
NONADMIN_USERNAME="${NONADMIN_USERNAME:-viewer}"
NONADMIN_PASSWORD="${NONADMIN_PASSWORD:-viewer}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_quota_enforce_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

STORAGE_DIR="${STORAGE_DIR:-${OUT_DIR}/storage}"
mkdir -p "$STORAGE_DIR"

export PYTHONPATH="${PYTHONPATH:-src}"

# Force an isolated ephemeral DB for this verification, even if the caller has
# YUANTUS_* env vars set (e.g., running via scripts/verify_all.sh).
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_STORAGE_TYPE="local"
export YUANTUS_LOCAL_STORAGE_PATH="$STORAGE_DIR"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

# Quota under test.
export YUANTUS_QUOTA_MODE="enforce"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin >/dev/null
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$NONADMIN_USERNAME" --password "$NONADMIN_PASSWORD" \
  --user-id 2 --roles viewer --no-superuser >/dev/null
"$YUANTUS_BIN" seed-meta >/dev/null

server_log="${OUT_DIR}/server.log"
log "Start API server (base=${BASE_URL})"
"$UVICORN_BIN" yuantus.api.app:app --host 127.0.0.1 --port "$PORT" >"$server_log" 2>&1 &
server_pid="$!"

cleanup() {
  kill "$server_pid" >/dev/null 2>&1 || true
  rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true
}
trap cleanup EXIT

log "Wait for /health"
for _ in {1..60}; do
  if curl -fsS "${BASE_URL}/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "${BASE_URL}/api/v1/health" >"${OUT_DIR}/health.json" || fail "health failed (see ${server_log})"

json_get() {
  "$PY_BIN" - "$1" "$2" <<'PY'
import json
import sys

path = sys.argv[2].split(".")
with open(sys.argv[1], "r", encoding="utf-8") as f:
  cur = json.load(f)
for key in path:
  if isinstance(cur, dict):
    cur = cur.get(key)
  else:
    cur = None
    break
print("" if cur is None else str(cur))
PY
}

assert_eq() {
  local label="$1"
  local got="$2"
  local want="$3"
  if [[ "$got" != "$want" ]]; then
    fail "${label}: expected '${want}', got '${got}'"
  fi
}

assert_nonempty() {
  local label="$1"
  local val="$2"
  if [[ -z "$val" ]]; then
    fail "${label}: expected non-empty"
  fi
}

log "Login (admin)"
login_json="${OUT_DIR}/login_admin.json"
code="$(
  curl -sS -o "$login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_json" >&2 || true
  fail "admin login -> HTTP $code"
fi
ADMIN_TOKEN="$("$PY_BIN" - "$login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "admin.access_token" "$ADMIN_TOKEN"

log "Login (non-admin)"
login_json="${OUT_DIR}/login_nonadmin.json"
code="$(
  curl -sS -o "$login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${NONADMIN_USERNAME}\",\"password\":\"${NONADMIN_PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_json" >&2 || true
  fail "non-admin login -> HTTP $code"
fi
NONADMIN_TOKEN="$("$PY_BIN" - "$login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "nonadmin.access_token" "$NONADMIN_TOKEN"

admin_header=(-H "Authorization: Bearer ${ADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
nonadmin_header=(-H "Authorization: Bearer ${NONADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

log "Non-admin should be forbidden on /admin/quota"
nonadmin_quota_json="${OUT_DIR}/quota_nonadmin.json"
code="$(
  curl -sS -o "$nonadmin_quota_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/quota" "${nonadmin_header[@]}"
)"
assert_eq "non-admin GET /admin/quota http_code" "$code" "403"

log "Admin quota should be accessible and mode=enforce"
quota_get_json="${OUT_DIR}/quota_get.json"
code="$(
  curl -sS -o "$quota_get_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/quota" "${admin_header[@]}"
)"
assert_eq "admin GET /admin/quota http_code" "$code" "200"
assert_eq "quota.mode" "$(json_get "$quota_get_json" mode)" "enforce"

log "Set max_files=1 via PUT /admin/quota"
quota_put_json="${OUT_DIR}/quota_put.json"
code="$(
  curl -sS -o "$quota_put_json" -w "%{http_code}" \
    -X PUT "${BASE_URL}/api/v1/admin/quota" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"max_files":1}'
)"
assert_eq "admin PUT /admin/quota http_code" "$code" "200"
assert_eq "quota.max_files" "$(json_get "$quota_put_json" quota.max_files)" "1"

log "Upload first file (should succeed under max_files=1)"
file1_path="${OUT_DIR}/file1.txt"
file2_path="${OUT_DIR}/file2.txt"
printf "quota-enforce-e2e file1 %s\n" "$timestamp" >"$file1_path"
printf "quota-enforce-e2e file2 %s\n" "$timestamp" >"$file2_path"

file1_json="${OUT_DIR}/file1_upload.json"
code="$(
  curl -sS -o "$file1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/file/upload?generate_preview=false" \
    "${admin_header[@]}" \
    -F "file=@${file1_path}"
)"
assert_eq "upload file1 http_code" "$code" "200"
file1_id="$(json_get "$file1_json" id)"
assert_nonempty "file1.id" "$file1_id"

log "Quota usage should show files=1"
quota_after1_json="${OUT_DIR}/quota_after_upload1.json"
code="$(
  curl -sS -o "$quota_after1_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/quota" "${admin_header[@]}"
)"
assert_eq "admin GET /admin/quota (after upload1) http_code" "$code" "200"
assert_eq "quota.usage.files" "$(json_get "$quota_after1_json" usage.files)" "1"

log "Upload second file (should fail with 429 QUOTA_EXCEEDED)"
file2_json="${OUT_DIR}/file2_upload.json"
code="$(
  curl -sS -o "$file2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/file/upload?generate_preview=false" \
    "${admin_header[@]}" \
    -F "file=@${file2_path}"
)"
assert_eq "upload file2 http_code" "$code" "429"
assert_eq "upload file2 detail.code" "$(json_get "$file2_json" detail.code)" "QUOTA_EXCEEDED"

log "Quota usage should remain files=1 after rejected upload"
quota_after2_json="${OUT_DIR}/quota_after_upload2.json"
code="$(
  curl -sS -o "$quota_after2_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/quota" "${admin_header[@]}"
)"
assert_eq "admin GET /admin/quota (after upload2) http_code" "$code" "200"
assert_eq "quota.usage.files (after upload2)" "$(json_get "$quota_after2_json" usage.files)" "1"

log "PASS: Quota enforcement E2E verification"

