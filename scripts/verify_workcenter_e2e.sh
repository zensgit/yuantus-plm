#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Manufacturing WorkCenters.
#
# Coverage:
# - create/list/get/update workcenters
# - integrate with routing operation by workcenter_code
# - guardrail: inactive workcenter cannot be assigned to operations (HTTP 400)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-workcenter/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_workcenter_${timestamp}.db}"
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

# Ensure auth is enforced.
export YUANTUS_AUTH_MODE="required"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
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

admin_header=(-H "Authorization: Bearer ${ADMIN_TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")

ts="$(date +%s)"
PLANT="PLANT-1"
LINE="LINE-1"
WC_CODE="WC-${ts}"

log "Create workcenter"
wc_create_json="${OUT_DIR}/workcenter_create.json"
code="$(
  curl -sS -o "$wc_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/workcenters" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"code\":\"${WC_CODE}\",\"name\":\"WorkCenter ${ts}\",\"plant_code\":\"${PLANT}\",\"department_code\":\"${LINE}\",\"is_active\":true}"
)"
assert_eq "workcenter create http_code" "$code" "200"
WC_ID="$(json_get "$wc_create_json" id)"
assert_nonempty "workcenter.id" "$WC_ID"
assert_eq "workcenter.code" "$(json_get "$wc_create_json" code)" "$WC_CODE"

log "List workcenters (plant_code filter; expect contains created)"
wc_list_json="${OUT_DIR}/workcenters_list.json"
code="$(
  curl -sS -o "$wc_list_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/workcenters?plant_code=${PLANT}&include_inactive=false" \
    "${admin_header[@]}"
)"
assert_eq "workcenters list http_code" "$code" "200"
"$PY_BIN" - "$wc_list_json" "$WC_ID" "$WC_CODE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  items = json.load(f)
target_id = sys.argv[2]
target_code = sys.argv[3]
if not isinstance(items, list):
  raise SystemExit("expected list")
found = any((i.get("id") == target_id and i.get("code") == target_code) for i in items)
if not found:
  raise SystemExit("workcenter not found in list")
print("workcenter_list_ok=1")
PY

log "Get workcenter"
wc_get_json="${OUT_DIR}/workcenter_get.json"
code="$(
  curl -sS -o "$wc_get_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/workcenters/${WC_ID}" \
    "${admin_header[@]}"
)"
assert_eq "workcenter get http_code" "$code" "200"
assert_eq "workcenter.get.code" "$(json_get "$wc_get_json" code)" "$WC_CODE"

log "Update workcenter name"
wc_update_json="${OUT_DIR}/workcenter_update.json"
code="$(
  curl -sS -o "$wc_update_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/workcenters/${WC_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"WorkCenter Updated ${ts}\"}"
)"
assert_eq "workcenter update http_code" "$code" "200"

log "Create EBOM + MBOM + routing (plant/line scoped)"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WC-P-${ts}\",\"name\":\"WorkCenter Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_json="${OUT_DIR}/child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WC-C-${ts}\",\"name\":\"WorkCenter Child\"}}"
)"
assert_eq "create child http_code" "$code" "200"
CHILD_ID="$(json_get "$child_json" id)"
assert_nonempty "child.id" "$CHILD_ID"

bom_add_json="${OUT_DIR}/bom_add.json"
code="$(
  curl -sS -o "$bom_add_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add parent->child http_code" "$code" "200"
assert_eq "add parent->child ok" "$(json_get "$bom_add_json" ok)" "True"

mbom_create_json="${OUT_DIR}/mbom_create.json"
code="$(
  curl -sS -o "$mbom_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/mboms/from-ebom" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"source_item_id\":\"${PARENT_ID}\",\"name\":\"MBOM-WC-${ts}\"}"
)"
assert_eq "mbom create http_code" "$code" "200"
MBOM_ID="$(json_get "$mbom_create_json" id)"
assert_nonempty "mbom.id" "$MBOM_ID"

routing_create_json="${OUT_DIR}/routing_create.json"
code="$(
  curl -sS -o "$routing_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"Routing-WC-${ts}\",\"mbom_id\":\"${MBOM_ID}\",\"plant_code\":\"${PLANT}\",\"line_code\":\"${LINE}\"}"
)"
assert_eq "routing create http_code" "$code" "200"
ROUTING_ID="$(json_get "$routing_create_json" id)"
assert_nonempty "routing.id" "$ROUTING_ID"

log "Add operation with workcenter_code (should resolve id+code)"
op1_json="${OUT_DIR}/op10_add.json"
code="$(
  curl -sS -o "$op1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"10\",\"name\":\"Cut\",\"workcenter_code\":\"${WC_CODE}\",\"setup_time\":5,\"run_time\":1}"
)"
assert_eq "add op10 http_code" "$code" "200"
assert_eq "op10.workcenter_code" "$(json_get "$op1_json" workcenter_code)" "$WC_CODE"
assert_nonempty "op10.workcenter_id" "$(json_get "$op1_json" workcenter_id)"

log "Deactivate workcenter and ensure routing op assignment fails"
wc_deactivate_json="${OUT_DIR}/workcenter_deactivate.json"
code="$(
  curl -sS -o "$wc_deactivate_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/workcenters/${WC_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"is_active\":false}"
)"
assert_eq "workcenter deactivate http_code" "$code" "200"

op2_err_json="${OUT_DIR}/op20_add_inactive_workcenter.json"
code="$(
  curl -sS -o "$op2_err_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"20\",\"name\":\"Assemble\",\"workcenter_code\":\"${WC_CODE}\",\"setup_time\":10,\"run_time\":2}"
)"
assert_eq "add op20 with inactive wc http_code" "$code" "400"
"$PY_BIN" - "$op2_err_json" "$WC_CODE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
detail = str(resp.get("detail") or "")
if sys.argv[2] not in detail or "inactive" not in detail.lower():
  raise SystemExit(f"unexpected detail: {detail}")
print("inactive_guardrail_ok=1")
PY

log "PASS: WorkCenter API E2E verification"

