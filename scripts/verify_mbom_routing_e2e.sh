#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Manufacturing MBOM + Routing.
#
# Coverage:
# - build a minimal EBOM (parent -> child)
# - create MBOM from EBOM via /api/v1/mboms/from-ebom
# - validate MBOM structure endpoint returns expected child
# - create routing and add operations
# - validate operations list ordering
# - calculate time/cost and validate numeric + expected totals
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-mbom-routing/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_mbom_routing_${timestamp}.db}"
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

log "Create EBOM parent + child"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MR-P-${ts}\",\"name\":\"MBOM Routing Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_json="${OUT_DIR}/child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MR-C-${ts}\",\"name\":\"MBOM Routing Child\"}}"
)"
assert_eq "create child http_code" "$code" "200"
CHILD_ID="$(json_get "$child_json" id)"
assert_nonempty "child.id" "$CHILD_ID"

log "Build EBOM (parent -> child)"
bom_add_json="${OUT_DIR}/bom_add_parent_child.json"
code="$(
  curl -sS -o "$bom_add_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_ID}\",\"quantity\":2,\"uom\":\"EA\"}"
)"
assert_eq "add parent->child http_code" "$code" "200"
assert_eq "add parent->child ok" "$(json_get "$bom_add_json" ok)" "True"

log "Create MBOM from EBOM"
mbom_create_json="${OUT_DIR}/mbom_create_from_ebom.json"
code="$(
  curl -sS -o "$mbom_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/mboms/from-ebom" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"source_item_id\":\"${PARENT_ID}\",\"name\":\"MBOM-${ts}\"}"
)"
assert_eq "mbom create http_code" "$code" "200"
MBOM_ID="$(json_get "$mbom_create_json" id)"
assert_nonempty "mbom.id" "$MBOM_ID"

"$PY_BIN" - "$mbom_create_json" "$CHILD_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
structure = resp.get("structure") or {}
children = structure.get("children") or []
if len(children) != 1:
  raise SystemExit(f"expected mbom.structure.children=1, got {len(children)}")

child_item = (children[0] or {}).get("item") or {}
if child_item.get("id") != sys.argv[2]:
  raise SystemExit(f"expected child.id={sys.argv[2]}, got {child_item.get('id')}")

print("mbom_create_ok=1")
PY

log "Get MBOM structure endpoint (expect child exists)"
mbom_get_json="${OUT_DIR}/mbom_get_structure.json"
code="$(
  curl -sS -o "$mbom_get_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/mboms/${MBOM_ID}" \
    "${admin_header[@]}"
)"
assert_eq "mbom get http_code" "$code" "200"
"$PY_BIN" - "$mbom_get_json" "$CHILD_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  struct = json.load(f)
children = struct.get("children") or []
if len(children) != 1:
  raise SystemExit(f"expected mbom.children=1, got {len(children)}")
child_item = (children[0] or {}).get("item") or {}
if child_item.get("id") != sys.argv[2]:
  raise SystemExit(f"expected child.id={sys.argv[2]}, got {child_item.get('id')}")
print("mbom_get_ok=1")
PY

log "Create routing for MBOM"
routing_create_json="${OUT_DIR}/routing_create.json"
code="$(
  curl -sS -o "$routing_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"Routing-${ts}\",\"mbom_id\":\"${MBOM_ID}\"}"
)"
assert_eq "routing create http_code" "$code" "200"
ROUTING_ID="$(json_get "$routing_create_json" id)"
assert_nonempty "routing.id" "$ROUTING_ID"

log "Add operations"
op1_json="${OUT_DIR}/routing_op_10_add.json"
code="$(
  curl -sS -o "$op1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"operation_number":"10","name":"Cut","setup_time":5,"run_time":1}'
)"
assert_eq "add op10 http_code" "$code" "200"
OP1_ID="$(json_get "$op1_json" id)"
assert_nonempty "op10.id" "$OP1_ID"

op2_json="${OUT_DIR}/routing_op_20_add.json"
code="$(
  curl -sS -o "$op2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"operation_number":"20","name":"Assemble","setup_time":10,"run_time":2}'
)"
assert_eq "add op20 http_code" "$code" "200"
OP2_ID="$(json_get "$op2_json" id)"
assert_nonempty "op20.id" "$OP2_ID"

log "List operations (expect 2, in order)"
ops_list_json="${OUT_DIR}/routing_ops_list.json"
code="$(
  curl -sS -o "$ops_list_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_ID}/operations" \
    "${admin_header[@]}"
)"
assert_eq "list ops http_code" "$code" "200"
"$PY_BIN" - "$ops_list_json" "$OP1_ID" "$OP2_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  ops = json.load(f)
if not isinstance(ops, list):
  raise SystemExit("expected list")
if len(ops) != 2:
  raise SystemExit(f"expected 2 ops, got {len(ops)}")
ids = [o.get("id") for o in ops]
if ids != [sys.argv[2], sys.argv[3]]:
  raise SystemExit(f"unexpected op order: {ids}")
seqs = [int(o.get("sequence") or 0) for o in ops]
if seqs != [10, 20]:
  raise SystemExit(f"unexpected sequences: {seqs}")
print("routing_ops_ok=1")
PY

log "Calculate time (quantity=5; expect total_time=30)"
time_json="${OUT_DIR}/routing_time_calc.json"
code="$(
  curl -sS -o "$time_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/calculate-time" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"quantity":5}'
)"
assert_eq "calc time http_code" "$code" "200"
"$PY_BIN" - "$time_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
total = float(resp.get("total_time") or 0)
setup = float(resp.get("setup_time") or 0)
run = float(resp.get("run_time") or 0)
if total != 30.0 or setup != 15.0 or run != 15.0:
  raise SystemExit(f"unexpected time totals: total={total} setup={setup} run={run}")
ops = resp.get("operations") or []
if len(ops) != 2:
  raise SystemExit(f"expected 2 ops in time calc, got {len(ops)}")
print("routing_time_ok=1")
PY

log "Calculate cost (quantity=5; expect total_cost=40, cost_per_unit=8)"
cost_json="${OUT_DIR}/routing_cost_calc.json"
code="$(
  curl -sS -o "$cost_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_ID}/calculate-cost" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"quantity":5}'
)"
assert_eq "calc cost http_code" "$code" "200"
"$PY_BIN" - "$cost_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
total = float(resp.get("total_cost") or 0)
cpu = float(resp.get("cost_per_unit") or 0)
labor = float(resp.get("labor_cost") or 0)
overhead = float(resp.get("overhead_cost") or 0)
if total != 40.0 or cpu != 8.0 or labor != 25.0 or overhead != 15.0:
  raise SystemExit(
    f"unexpected cost: total={total} cpu={cpu} labor={labor} overhead={overhead}"
  )
print("routing_cost_ok=1")
PY

log "PASS: MBOM + Routing API E2E verification"

