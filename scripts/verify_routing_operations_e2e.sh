#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Manufacturing Routing operation management.
#
# Coverage:
# - build a minimal EBOM (parent -> child) and create MBOM + routing
# - create/list/update/resequence/delete operations:
#   - PATCH /api/v1/routings/{routing_id}/operations/{operation_id}
#   - POST  /api/v1/routings/{routing_id}/operations/resequence
#   - DELETE /api/v1/routings/{routing_id}/operations/{operation_id}
# - validate routing totals are updated (setup/run/labor)
# - validate workcenter guardrails during operation updates:
#   - unknown workcenter_code -> 404
#   - inactive workcenter -> 400
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-routing-operations/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_routing_operations_${timestamp}.db}"
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

log "Create EBOM parent + child"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"RO-P-${ts}\",\"name\":\"Routing Ops Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_json="${OUT_DIR}/child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"RO-C-${ts}\",\"name\":\"Routing Ops Child\"}}"
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
    -d "{\"source_item_id\":\"${PARENT_ID}\",\"name\":\"MBOM-RO-${ts}\"}"
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
    -d "{\"name\":\"Routing-RO-${ts}\",\"mbom_id\":\"${MBOM_ID}\",\"plant_code\":\"${PLANT}\",\"line_code\":\"${LINE}\"}"
)"
assert_eq "routing create http_code" "$code" "200"
ROUTING_ID="$(json_get "$routing_create_json" id)"
assert_nonempty "routing.id" "$ROUTING_ID"

log "Create a WorkCenter"
WC_CODE="WC-RO-${ts}"
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

log "Add 3 operations"
op1_json="${OUT_DIR}/op10_add.json"
code="$(
  curl -sS -o "$op1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"10\",\"name\":\"Cut\",\"setup_time\":5,\"run_time\":1,\"workcenter_code\":\"${WC_CODE}\"}"
)"
assert_eq "add op10 http_code" "$code" "200"
OP1_ID="$(json_get "$op1_json" id)"
assert_nonempty "op10.id" "$OP1_ID"

op2_json="${OUT_DIR}/op20_add.json"
code="$(
  curl -sS -o "$op2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"20\",\"name\":\"Assemble\",\"setup_time\":10,\"run_time\":2}"
)"
assert_eq "add op20 http_code" "$code" "200"
OP2_ID="$(json_get "$op2_json" id)"
assert_nonempty "op20.id" "$OP2_ID"

op3_json="${OUT_DIR}/op30_add.json"
code="$(
  curl -sS -o "$op3_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"30\",\"name\":\"Inspect\",\"setup_time\":7,\"run_time\":3}"
)"
assert_eq "add op30 http_code" "$code" "200"
OP3_ID="$(json_get "$op3_json" id)"
assert_nonempty "op30.id" "$OP3_ID"

log "Get routing totals (expect setup=22, run=6, labor=28)"
routing_get_json="${OUT_DIR}/routing_get_totals_1.json"
code="$(
  curl -sS -o "$routing_get_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}" \
    "${admin_header[@]}"
)"
assert_eq "routing get http_code" "$code" "200"
"$PY_BIN" - "$routing_get_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  r = json.load(f)

def fnum(v):
  try:
    return float(v)
  except Exception:
    return 0.0

setup = fnum(r.get("total_setup_time"))
run = fnum(r.get("total_run_time"))
labor = fnum(r.get("total_labor_time"))

if setup != 22.0 or run != 6.0 or labor != 28.0:
  raise SystemExit(f"unexpected totals: setup={setup} run={run} labor={labor}")
print("routing_totals_1_ok=1")
PY

log "List operations (expect order op10,op20,op30 with seq 10,20,30)"
ops_list_json="${OUT_DIR}/ops_list_1.json"
code="$(
  curl -sS -o "$ops_list_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}"
)"
assert_eq "list ops http_code" "$code" "200"
"$PY_BIN" - "$ops_list_json" "$OP1_ID" "$OP2_ID" "$OP3_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  ops = json.load(f)
ids = [o.get("id") for o in ops]
if ids != [sys.argv[2], sys.argv[3], sys.argv[4]]:
  raise SystemExit(f"unexpected op order: {ids}")
seqs = [int(o.get("sequence") or 0) for o in ops]
if seqs != [10, 20, 30]:
  raise SystemExit(f"unexpected sequences: {seqs}")
print("ops_list_1_ok=1")
PY

log "Update op20: move sequence to 5, adjust time and labor, set work_instructions"
op2_update_json="${OUT_DIR}/op20_update.json"
code="$(
  curl -sS -o "$op2_update_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/${OP2_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"sequence":5,"setup_time":12,"run_time":4,"labor_setup_time":12,"labor_run_time":4,"work_instructions":"Updated WI"}'
)"
assert_eq "update op20 http_code" "$code" "200"
assert_eq "op20 sequence" "$(json_get "$op2_update_json" sequence)" "5"

log "List operations after op20 update (expect op20 first)"
ops_list_json2="${OUT_DIR}/ops_list_2_after_update.json"
code="$(
  curl -sS -o "$ops_list_json2" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}"
)"
assert_eq "list ops after update http_code" "$code" "200"
"$PY_BIN" - "$ops_list_json2" "$OP2_ID" "$OP1_ID" "$OP3_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  ops = json.load(f)
ids = [o.get("id") for o in ops]
if ids != [sys.argv[2], sys.argv[3], sys.argv[4]]:
  raise SystemExit(f"unexpected op order after update: {ids}")
print("ops_list_after_update_ok=1")
PY

log "Routing totals after op20 update (expect setup=24, run=8, labor=32)"
routing_get_json2="${OUT_DIR}/routing_get_totals_2.json"
code="$(
  curl -sS -o "$routing_get_json2" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}" \
    "${admin_header[@]}"
)"
assert_eq "routing get 2 http_code" "$code" "200"
"$PY_BIN" - "$routing_get_json2" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  r = json.load(f)

def fnum(v):
  try:
    return float(v)
  except Exception:
    return 0.0

# op20 setup/run changed from 10/2 to 12/4, so totals:
# setup = 5 + 12 + 7 = 24
# run   = 1 + 4 + 3 = 8
# labor = (5+1) + (12+4) + (7+3) = 32
setup = fnum(r.get("total_setup_time"))
run = fnum(r.get("total_run_time"))
labor = fnum(r.get("total_labor_time"))

if setup != 24.0 or run != 8.0 or labor != 32.0:
  raise SystemExit(f"unexpected totals after update: setup={setup} run={run} labor={labor}")
print("routing_totals_2_ok=1")
PY

log "Resequence guardrail: duplicates -> HTTP 400"
resequence_dup_json="${OUT_DIR}/resequence_dup_err.json"
code="$(
  curl -sS -o "$resequence_dup_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/resequence" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"ordered_operation_ids\":[\"${OP1_ID}\",\"${OP1_ID}\",\"${OP3_ID}\"]}"
)"
assert_eq "resequence duplicates http_code" "$code" "400"

log "Resequence guardrail: omitted id -> HTTP 400"
resequence_omit_json="${OUT_DIR}/resequence_omit_err.json"
code="$(
  curl -sS -o "$resequence_omit_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/resequence" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"ordered_operation_ids\":[\"${OP1_ID}\",\"${OP3_ID}\"]}"
)"
assert_eq "resequence omitted id http_code" "$code" "400"

log "Resequence OK: order op30,op10,op20"
resequence_ok_json="${OUT_DIR}/resequence_ok.json"
code="$(
  curl -sS -o "$resequence_ok_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/resequence" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"ordered_operation_ids\":[\"${OP3_ID}\",\"${OP1_ID}\",\"${OP2_ID}\"]}"
)"
assert_eq "resequence ok http_code" "$code" "200"
"$PY_BIN" - "$resequence_ok_json" "$OP3_ID" "$OP1_ID" "$OP2_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  ops = json.load(f)
ids = [o.get("id") for o in ops]
if ids != [sys.argv[2], sys.argv[3], sys.argv[4]]:
  raise SystemExit(f"unexpected resequence response order: {ids}")
seqs = [int(o.get("sequence") or 0) for o in ops]
if seqs != [10, 20, 30]:
  raise SystemExit(f"unexpected resequence sequences: {seqs}")
print("resequence_ok=1")
PY

log "Delete op10 (expect remaining 2 ops resequenced)"
delete_json="${OUT_DIR}/op10_delete.json"
code="$(
  curl -sS -o "$delete_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/${OP1_ID}" \
    "${admin_header[@]}"
)"
assert_eq "delete op10 http_code" "$code" "200"
assert_eq "delete op10.deleted" "$(json_get "$delete_json" deleted)" "True"

ops_list_json3="${OUT_DIR}/ops_list_3_after_delete.json"
code="$(
  curl -sS -o "$ops_list_json3" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}"
)"
assert_eq "list ops after delete http_code" "$code" "200"
"$PY_BIN" - "$ops_list_json3" "$OP3_ID" "$OP2_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  ops = json.load(f)
if len(ops) != 2:
  raise SystemExit(f"expected 2 ops after delete, got {len(ops)}")
ids = [o.get("id") for o in ops]
if ids != [sys.argv[2], sys.argv[3]]:
  raise SystemExit(f"unexpected op order after delete: {ids}")
seqs = [int(o.get('sequence') or 0) for o in ops]
if seqs != [10, 20]:
  raise SystemExit(f"unexpected sequences after delete: {seqs}")
print("ops_after_delete_ok=1")
PY

log "Workcenter guardrail via update: unknown workcenter_code -> 404"
unknown_wc_json="${OUT_DIR}/op_update_unknown_workcenter.json"
code="$(
  curl -sS -o "$unknown_wc_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/${OP2_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"workcenter_code":"WC-UNKNOWN-XYZ"}'
)"
assert_eq "update op unknown workcenter http_code" "$code" "404"

log "Deactivate workcenter and validate update blocked (inactive -> 400)"
wc_deactivate_json="${OUT_DIR}/workcenter_deactivate.json"
code="$(
  curl -sS -o "$wc_deactivate_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/workcenters/${WC_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"is_active":false}'
)"
assert_eq "workcenter deactivate http_code" "$code" "200"

inactive_wc_json="${OUT_DIR}/op_update_inactive_workcenter.json"
code="$(
  curl -sS -o "$inactive_wc_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations/${OP2_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"workcenter_code\":\"${WC_CODE}\"}"
)"
assert_eq "update op inactive workcenter http_code" "$code" "400"
"$PY_BIN" - "$inactive_wc_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
detail = str(resp.get("detail") or "")
if "inactive" not in detail.lower():
  raise SystemExit(f"unexpected detail: {detail}")
print("inactive_guardrail_ok=1")
PY

log "PASS: Routing operations API E2E verification"

