#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Manufacturing Routing copy.
#
# Coverage:
# - build a minimal EBOM (parent -> child) and create MBOM + routing + operations
# - copy routing (and operations) via: POST /api/v1/routings/{routing_id}/copy?new_name=...
# - validate:
#   - copied routing is not primary
#   - operations are copied (count + basic fields)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-routing-copy/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_routing_copy_${timestamp}.db}"
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
WC_CODE="WC-COPY-${ts}"

log "Create EBOM parent + child"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"RC-P-${ts}\",\"name\":\"Routing Copy Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_json="${OUT_DIR}/child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"RC-C-${ts}\",\"name\":\"Routing Copy Child\"}}"
)"
assert_eq "create child http_code" "$code" "200"
CHILD_ID="$(json_get "$child_json" id)"
assert_nonempty "child.id" "$CHILD_ID"

log "Build EBOM (parent -> child)"
bom_add_json="${OUT_DIR}/bom_add.json"
code="$(
  curl -sS -o "$bom_add_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add parent->child http_code" "$code" "200"
assert_eq "add parent->child ok" "$(json_get "$bom_add_json" ok)" "True"

log "Create MBOM from EBOM"
mbom_create_json="${OUT_DIR}/mbom_create.json"
code="$(
  curl -sS -o "$mbom_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/mboms/from-ebom" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"source_item_id\":\"${PARENT_ID}\",\"name\":\"MBOM-RC-${ts}\"}"
)"
assert_eq "mbom create http_code" "$code" "200"
MBOM_ID="$(json_get "$mbom_create_json" id)"
assert_nonempty "mbom.id" "$MBOM_ID"

log "Create routing for MBOM"
routing_create_json="${OUT_DIR}/routing_create.json"
code="$(
  curl -sS -o "$routing_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"Routing-RC-${ts}\",\"mbom_id\":\"${MBOM_ID}\",\"plant_code\":\"${PLANT}\",\"line_code\":\"${LINE}\"}"
)"
assert_eq "routing create http_code" "$code" "200"
ROUTING_ID="$(json_get "$routing_create_json" id)"
assert_nonempty "routing.id" "$ROUTING_ID"
assert_eq "routing is_primary" "$(json_get "$routing_create_json" is_primary)" "True"

log "Create WorkCenter and add 2 operations"
wc_create_json="${OUT_DIR}/workcenter_create.json"
code="$(
  curl -sS -o "$wc_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/workcenters" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"code\":\"${WC_CODE}\",\"name\":\"WorkCenter ${ts}\",\"plant_code\":\"${PLANT}\",\"department_code\":\"${LINE}\",\"is_active\":true}"
)"
assert_eq "workcenter create http_code" "$code" "200"

op1_json="${OUT_DIR}/op10_add.json"
code="$(
  curl -sS -o "$op1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"10\",\"name\":\"Cut\",\"setup_time\":5,\"run_time\":1,\"workcenter_code\":\"${WC_CODE}\"}"
)"
assert_eq "add op10 http_code" "$code" "200"

op2_json="${OUT_DIR}/op20_add.json"
code="$(
  curl -sS -o "$op2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"20\",\"name\":\"Assemble\",\"setup_time\":10,\"run_time\":2}"
)"
assert_eq "add op20 http_code" "$code" "200"

log "Copy routing"
copy_json="${OUT_DIR}/routing_copy.json"
new_name="Routing-RC-COPY-${ts}"
code="$(
  curl -sS -o "$copy_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/copy?new_name=${new_name}" \
    "${admin_header[@]}"
)"
assert_eq "routing copy http_code" "$code" "200"
COPIED_ID="$(json_get "$copy_json" id)"
assert_nonempty "copied.id" "$COPIED_ID"
assert_eq "copied.name" "$(json_get "$copy_json" name)" "$new_name"
assert_eq "copied.mbom_id" "$(json_get "$copy_json" mbom_id)" "$MBOM_ID"
assert_eq "copied.is_primary" "$(json_get "$copy_json" is_primary)" "False"

log "Source routing remains primary"
source_get_json="${OUT_DIR}/routing_source_get.json"
code="$(
  curl -sS -o "$source_get_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}" \
    "${admin_header[@]}"
)"
assert_eq "routing source get http_code" "$code" "200"
assert_eq "routing source is_primary" "$(json_get "$source_get_json" is_primary)" "True"

log "Copied operations list (expect 2 ops with numbers 10,20; op10 has workcenter_code)"
copy_ops_json="${OUT_DIR}/routing_copy_ops_list.json"
code="$(
  curl -sS -o "$copy_ops_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${COPIED_ID}/operations" \
    "${admin_header[@]}"
)"
assert_eq "copied ops list http_code" "$code" "200"
"$PY_BIN" - "$copy_ops_json" "$WC_CODE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  ops = json.load(f)
if not isinstance(ops, list) or len(ops) != 2:
  raise SystemExit(f"expected 2 ops, got {type(ops).__name__} len={len(ops) if isinstance(ops, list) else 'n/a'}")

nums = [str(o.get("operation_number")) for o in ops]
if nums != ["10", "20"]:
  raise SystemExit(f"unexpected operation_number list: {nums}")

seqs = [int(o.get("sequence") or 0) for o in ops]
if seqs != [10, 20]:
  raise SystemExit(f"unexpected sequences: {seqs}")

wc_code = str((ops[0] or {}).get("workcenter_code") or "")
if wc_code != sys.argv[2]:
  raise SystemExit(f"expected op10 workcenter_code={sys.argv[2]}, got {wc_code}")

print("routing_copy_ops_ok=1")
PY

log "PASS: Routing copy API E2E verification"

