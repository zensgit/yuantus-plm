#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Version-File Binding.
#
# Coverage:
# - create Part + init version
# - upload file, attach to item
# - ensure attaching version file without checkout is blocked (409)
# - checkout version (locks files)
# - attach file to version as owner
# - ensure non-owner cannot attach while checked out by someone else (409)
# - checkin and verify /versions/{id}/files contains expected role binding
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-version-file-binding/${timestamp}"
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
VIEWER_USERNAME="${VIEWER_USERNAME:-viewer}"
VIEWER_PASSWORD="${VIEWER_PASSWORD:-viewer}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_version_file_binding_${timestamp}.db}"
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

# Ensure auth is enforced (avoid get_current_user_id_optional defaulting to user_id=1).
export YUANTUS_AUTH_MODE="required"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin >/dev/null
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$VIEWER_USERNAME" --password "$VIEWER_PASSWORD" \
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
login_admin_json="${OUT_DIR}/login_admin.json"
code="$(
  curl -sS -o "$login_admin_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_admin_json" >&2 || true
  fail "admin login -> HTTP $code"
fi
ADMIN_TOKEN="$("$PY_BIN" - "$login_admin_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "admin.access_token" "$ADMIN_TOKEN"

log "Login (viewer)"
login_viewer_json="${OUT_DIR}/login_viewer.json"
code="$(
  curl -sS -o "$login_viewer_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${VIEWER_USERNAME}\",\"password\":\"${VIEWER_PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_viewer_json" >&2 || true
  fail "viewer login -> HTTP $code"
fi
VIEWER_TOKEN="$("$PY_BIN" - "$login_viewer_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "viewer.access_token" "$VIEWER_TOKEN"

admin_header=(-H "Authorization: Bearer ${ADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
viewer_header=(-H "Authorization: Bearer ${VIEWER_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

log "Create Part"
ts="$(date +%s)"
part_json="${OUT_DIR}/part_create.json"
code="$(
  curl -sS -o "$part_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"VF-${ts}\",\"name\":\"Version File Bind\"}}"
)"
assert_eq "create part http_code" "$code" "200"
ITEM_ID="$(json_get "$part_json" id)"
assert_nonempty "part.id" "$ITEM_ID"

log "Init version"
ver_json="${OUT_DIR}/version_init.json"
code="$(
  curl -sS -o "$ver_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/init" \
    "${admin_header[@]}"
)"
assert_eq "init version http_code" "$code" "200"
VERSION_ID="$(json_get "$ver_json" id)"
assert_nonempty "version.id" "$VERSION_ID"

log "Upload file"
test_file="${OUT_DIR}/version_file_${ts}.txt"
echo "version-file-bind ${ts}" >"$test_file"
upload_json="${OUT_DIR}/file_upload.json"
code="$(
  curl -sS -o "$upload_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/file/upload" \
    "${admin_header[@]}" \
    -F "file=@${test_file};filename=version_file_${ts}.txt"
)"
assert_eq "upload http_code" "$code" "200"
FILE_ID="$(json_get "$upload_json" id)"
assert_nonempty "upload.id" "$FILE_ID"

log "Attach file to version without checkout should be blocked (409)"
vf_pre_json="${OUT_DIR}/version_file_attach_without_checkout.json"
code="$(
  curl -sS -o "$vf_pre_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/${VERSION_ID}/files" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"file_id\":\"${FILE_ID}\",\"file_role\":\"native_cad\",\"is_primary\":true,\"sequence\":0}"
)"
assert_eq "attach version file without checkout http_code" "$code" "409"

log "Attach file to item (native_cad)"
attach_item_json="${OUT_DIR}/file_attach_item.json"
code="$(
  curl -sS -o "$attach_item_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/file/attach" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"item_id\":\"${ITEM_ID}\",\"file_id\":\"${FILE_ID}\",\"file_role\":\"native_cad\"}"
)"
assert_eq "attach file to item http_code" "$code" "200"
assert_nonempty "attach.status" "$(json_get "$attach_item_json" status)"

log "Checkout version (lock files)"
checkout_json="${OUT_DIR}/version_checkout.json"
code="$(
  curl -sS -o "$checkout_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkout" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"lock files\"}"
)"
assert_eq "checkout http_code" "$code" "200"
CHECKOUT_ID="$(json_get "$checkout_json" id)"
assert_nonempty "checkout.id" "$CHECKOUT_ID"

log "Attach file to version (owner)"
vf_attach_json="${OUT_DIR}/version_file_attach.json"
code="$(
  curl -sS -o "$vf_attach_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/${VERSION_ID}/files" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"file_id\":\"${FILE_ID}\",\"file_role\":\"native_cad\",\"is_primary\":true,\"sequence\":0}"
)"
assert_eq "attach version file http_code" "$code" "200"
VF_ID="$(json_get "$vf_attach_json" id)"
assert_nonempty "version_file.id" "$VF_ID"

log "Non-owner attach should be blocked (409)"
viewer_attach_json="${OUT_DIR}/viewer_attach_blocked.json"
code="$(
  curl -sS -o "$viewer_attach_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/file/attach" \
    "${viewer_header[@]}" -H 'content-type: application/json' \
    -d "{\"item_id\":\"${ITEM_ID}\",\"file_id\":\"${FILE_ID}\",\"file_role\":\"attachment\"}"
)"
assert_eq "viewer attach blocked http_code" "$code" "409"

log "Checkin version (sync files)"
checkin_json="${OUT_DIR}/version_checkin.json"
code="$(
  curl -sS -o "$checkin_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/versions/items/${ITEM_ID}/checkin" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"comment\":\"sync files\"}"
)"
assert_eq "checkin http_code" "$code" "200"
CHECKIN_ID="$(json_get "$checkin_json" id)"
assert_nonempty "checkin.id" "$CHECKIN_ID"

log "Verify version files"
files_json="${OUT_DIR}/version_files_list.json"
code="$(
  curl -sS -o "$files_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/versions/${VERSION_ID}/files" "${admin_header[@]}"
)"
assert_eq "list version files http_code" "$code" "200"
"$PY_BIN" - "$files_json" "$FILE_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
file_id = sys.argv[2]
roles = [vf.get("file_role") for vf in (data or []) if vf.get("file_id") == file_id]
if "native_cad" not in roles:
  raise SystemExit(f"expected native_cad for file {file_id}, got {roles}")
print("version_files_ok=1")
PY

log "PASS: Version-file binding E2E verification"

