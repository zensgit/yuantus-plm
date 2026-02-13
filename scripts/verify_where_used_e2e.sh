#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Where-Used (reverse BOM lookup).
#
# Coverage:
# - create a simple BOM hierarchy:
#     ASSEMBLY -> SUBASSY -> COMPONENT
#     ASSEMBLY2 -> COMPONENT
# - where-used non-recursive: COMPONENT direct parents are SUBASSY + ASSEMBLY2 (count=2)
# - where-used recursive: includes ASSEMBLY as an ancestor (count=3, levels 1/2)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-where-used/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_where_used_${timestamp}.db}"
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

# Ensure auth is enforced (avoid optional user_id fallbacks in dev routers).
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

log "Create Parts (assembly/subassy/component/assembly2)"
assembly_json="${OUT_DIR}/part_assembly.json"
code="$(
  curl -sS -o "$assembly_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-ASSY-${ts}\",\"name\":\"Assembly ${ts}\"}}"
)"
assert_eq "create assembly http_code" "$code" "200"
ASSEMBLY_ID="$(json_get "$assembly_json" id)"
assert_nonempty "assembly.id" "$ASSEMBLY_ID"

subassy_json="${OUT_DIR}/part_subassy.json"
code="$(
  curl -sS -o "$subassy_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-SUBASSY-${ts}\",\"name\":\"Sub-Assembly ${ts}\"}}"
)"
assert_eq "create subassy http_code" "$code" "200"
SUBASSY_ID="$(json_get "$subassy_json" id)"
assert_nonempty "subassy.id" "$SUBASSY_ID"

component_json="${OUT_DIR}/part_component.json"
code="$(
  curl -sS -o "$component_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-COMP-${ts}\",\"name\":\"Component ${ts}\"}}"
)"
assert_eq "create component http_code" "$code" "200"
COMPONENT_ID="$(json_get "$component_json" id)"
assert_nonempty "component.id" "$COMPONENT_ID"

assembly2_json="${OUT_DIR}/part_assembly2.json"
code="$(
  curl -sS -o "$assembly2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"WU-ASSY2-${ts}\",\"name\":\"Assembly2 ${ts}\"}}"
)"
assert_eq "create assembly2 http_code" "$code" "200"
ASSEMBLY2_ID="$(json_get "$assembly2_json" id)"
assert_nonempty "assembly2.id" "$ASSEMBLY2_ID"

log "Build BOM"
add_1_json="${OUT_DIR}/bom_add_assembly_subassy.json"
code="$(
  curl -sS -o "$add_1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${ASSEMBLY_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${SUBASSY_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add child (assembly->subassy) http_code" "$code" "200"
assert_eq "add child (assembly->subassy) ok" "$(json_get "$add_1_json" ok)" "True"

add_2_json="${OUT_DIR}/bom_add_subassy_component.json"
code="$(
  curl -sS -o "$add_2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${SUBASSY_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${COMPONENT_ID}\",\"quantity\":2,\"uom\":\"EA\"}"
)"
assert_eq "add child (subassy->component) http_code" "$code" "200"
assert_eq "add child (subassy->component) ok" "$(json_get "$add_2_json" ok)" "True"

add_3_json="${OUT_DIR}/bom_add_assembly2_component.json"
code="$(
  curl -sS -o "$add_3_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${ASSEMBLY2_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${COMPONENT_ID}\",\"quantity\":4,\"uom\":\"EA\"}"
)"
assert_eq "add child (assembly2->component) http_code" "$code" "200"
assert_eq "add child (assembly2->component) ok" "$(json_get "$add_3_json" ok)" "True"

log "Where-used non-recursive (expect 2 direct parents)"
wu_json="${OUT_DIR}/where_used_non_recursive.json"
code="$(
  curl -sS -o "$wu_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${COMPONENT_ID}/where-used?recursive=false" "${admin_header[@]}"
)"
assert_eq "where-used non-recursive http_code" "$code" "200"
assert_eq "where-used non-recursive count" "$(json_get "$wu_json" count)" "2"
"$PY_BIN" - "$wu_json" "$SUBASSY_ID" "$ASSEMBLY2_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
parents = data.get("parents") or []
ids = [((p.get("parent") or {}).get("id")) for p in parents]
expect1, expect2 = sys.argv[2], sys.argv[3]
missing = [e for e in (expect1, expect2) if e not in ids]
if missing:
  raise SystemExit(f"missing direct parents: {missing}; got={ids}")
print("where_used_non_recursive_ok=1")
PY

log "Where-used recursive (expect 3 including ancestor assembly)"
wu_rec_json="${OUT_DIR}/where_used_recursive.json"
code="$(
  curl -sS -o "$wu_rec_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${COMPONENT_ID}/where-used?recursive=true&max_levels=5" "${admin_header[@]}"
)"
assert_eq "where-used recursive http_code" "$code" "200"
assert_eq "where-used recursive count" "$(json_get "$wu_rec_json" count)" "3"
"$PY_BIN" - "$wu_rec_json" "$SUBASSY_ID" "$ASSEMBLY2_ID" "$ASSEMBLY_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
parents = data.get("parents") or []
ids = [((p.get("parent") or {}).get("id")) for p in parents]
expect = set(sys.argv[2:])
missing = [e for e in expect if e not in ids]
if missing:
  raise SystemExit(f"missing parents in recursive response: {missing}; got={ids}")

# Validate level for the assembly ancestor is 2 (via component -> subassy -> assembly)
levels = {((p.get("parent") or {}).get("id")): p.get("level") for p in parents if (p.get("parent") or {}).get("id")}
assembly_id = sys.argv[4]
if levels.get(assembly_id) != 2:
  raise SystemExit(f"expected assembly level=2, got {levels.get(assembly_id)} (levels={levels})")
print("where_used_recursive_ok=1")
PY

log "PASS: Where-Used API E2E verification"

