#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Platform Admin tenant provisioning.
#
# Coverage:
# - platform admin enablement (YUANTUS_PLATFORM_ADMIN_ENABLED=true)
# - create tenant (+ default org + tenant admin user) via /api/v1/admin/tenants
# - list tenants + list orgs for tenant (platform admin-only)
# - RBAC guardrail: a tenant superuser from a non-platform tenant cannot access platform admin endpoints
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-platform-tenant-provisioning/${timestamp}"
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

PLATFORM_TENANT_ID="${PLATFORM_TENANT_ID:-platform}"
PLATFORM_ORG_ID="${PLATFORM_ORG_ID:-platform-org}"
PLATFORM_ADMIN_USERNAME="${PLATFORM_ADMIN_USERNAME:-admin}"
PLATFORM_ADMIN_PASSWORD="${PLATFORM_ADMIN_PASSWORD:-admin}"

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_platform_tenant_prov_${timestamp}.db}"
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

# Platform admin under test.
export YUANTUS_PLATFORM_ADMIN_ENABLED="true"
export YUANTUS_PLATFORM_TENANT_ID="$PLATFORM_TENANT_ID"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed platform admin identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$PLATFORM_TENANT_ID" --org "$PLATFORM_ORG_ID" \
  --username "$PLATFORM_ADMIN_USERNAME" --password "$PLATFORM_ADMIN_PASSWORD" \
  --user-id 1 --roles admin >/dev/null
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

log "Login as platform admin"
platform_login_json="${OUT_DIR}/login_platform_admin.json"
code="$(
  curl -sS -o "$platform_login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${PLATFORM_TENANT_ID}\",\"org_id\":\"${PLATFORM_ORG_ID}\",\"username\":\"${PLATFORM_ADMIN_USERNAME}\",\"password\":\"${PLATFORM_ADMIN_PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$platform_login_json" >&2 || true
  fail "platform admin login -> HTTP $code"
fi
PLATFORM_TOKEN="$("$PY_BIN" - "$platform_login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "platform_admin.access_token" "$PLATFORM_TOKEN"

platform_header=(-H "Authorization: Bearer ${PLATFORM_TOKEN}" -H "x-tenant-id: ${PLATFORM_TENANT_ID}" -H "x-org-id: ${PLATFORM_ORG_ID}")

log "List tenants as platform admin"
tenants_list_json="${OUT_DIR}/tenants_list.json"
code="$(
  curl -sS -o "$tenants_list_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/tenants" "${platform_header[@]}"
)"
assert_eq "platform GET /admin/tenants http_code" "$code" "200"

log "Create a new tenant (with default org + admin user)"
ts="$(date +%s)"
new_tenant_id="tenant-e2e-${ts}"
new_org_id="org-1"
new_admin_username="tenant-admin-${ts}"
new_admin_password="admin"

tenant_create_json="${OUT_DIR}/tenant_create.json"
code="$(
  curl -sS -o "$tenant_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/admin/tenants" \
    "${platform_header[@]}" -H 'content-type: application/json' \
    -d "{
      \"id\": \"${new_tenant_id}\",
      \"name\": \"Tenant E2E ${ts}\",
      \"is_active\": true,
      \"create_default_org\": true,
      \"default_org_id\": \"${new_org_id}\",
      \"admin_username\": \"${new_admin_username}\",
      \"admin_password\": \"${new_admin_password}\",
      \"admin_email\": \"${new_admin_username}@example.com\"
    }"
)"
assert_eq "platform POST /admin/tenants http_code" "$code" "200"
assert_eq "tenant_create.id" "$(json_get "$tenant_create_json" id)" "$new_tenant_id"

log "List orgs for new tenant"
tenant_orgs_json="${OUT_DIR}/tenant_orgs.json"
code="$(
  curl -sS -o "$tenant_orgs_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/tenants/${new_tenant_id}/orgs" "${platform_header[@]}"
)"
assert_eq "platform GET /admin/tenants/{id}/orgs http_code" "$code" "200"
"$PY_BIN" - "$tenant_orgs_json" "$new_org_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
oid = sys.argv[2]
items = data.get("items") or []
if not any(isinstance(o, dict) and o.get("id") == oid for o in items):
  raise SystemExit("expected default org in list_orgs_for_tenant response")
print("tenant_default_org_ok=1")
PY

log "Login as the new tenant admin"
tenant_admin_login_json="${OUT_DIR}/login_tenant_admin.json"
code="$(
  curl -sS -o "$tenant_admin_login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${new_tenant_id}\",\"org_id\":\"${new_org_id}\",\"username\":\"${new_admin_username}\",\"password\":\"${new_admin_password}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$tenant_admin_login_json" >&2 || true
  fail "tenant admin login -> HTTP $code"
fi
TENANT_ADMIN_TOKEN="$("$PY_BIN" - "$tenant_admin_login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
assert_nonempty "tenant_admin.access_token" "$TENANT_ADMIN_TOKEN"

tenant_admin_header=(-H "Authorization: Bearer ${TENANT_ADMIN_TOKEN}" -H "x-tenant-id: ${new_tenant_id}" -H "x-org-id: ${new_org_id}")

log "Tenant admin must NOT have platform admin access"
tenant_admin_tenants_json="${OUT_DIR}/tenant_admin_tenants.json"
code="$(
  curl -sS -o "$tenant_admin_tenants_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/tenants" "${tenant_admin_header[@]}"
)"
assert_eq "tenant admin GET /admin/tenants http_code" "$code" "403"

log "Tenant admin should have tenant-local superuser access (list orgs)"
orgs_json="${OUT_DIR}/tenant_admin_orgs.json"
code="$(
  curl -sS -o "$orgs_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/admin/orgs" "${tenant_admin_header[@]}"
)"
assert_eq "tenant admin GET /admin/orgs http_code" "$code" "200"
"$PY_BIN" - "$orgs_json" "$new_org_id" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
oid = sys.argv[2]
items = data.get("items") or []
if not any(isinstance(o, dict) and o.get("id") == oid for o in items):
  raise SystemExit("expected org in /admin/orgs response")
print("tenant_admin_orgs_ok=1")
PY

log "PASS: Platform tenant provisioning E2E verification"

