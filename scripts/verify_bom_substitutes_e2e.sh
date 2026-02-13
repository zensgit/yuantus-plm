#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for BOM Substitutes.
#
# Coverage:
# - create parent/child + BOM line
# - add/list/delete substitutes on the BOM line
# - guardrail: duplicate add should return 400
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-bom-substitutes/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_bom_substitutes_${timestamp}.db}"
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

log "Create parent/child/substitute items"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-A-${ts}\",\"name\":\"Substitute Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_json="${OUT_DIR}/child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-C-${ts}\",\"name\":\"Primary Child\"}}"
)"
assert_eq "create child http_code" "$code" "200"
CHILD_ID="$(json_get "$child_json" id)"
assert_nonempty "child.id" "$CHILD_ID"

sub1_json="${OUT_DIR}/sub1_create.json"
code="$(
  curl -sS -o "$sub1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-S1-${ts}\",\"name\":\"Substitute 1\"}}"
)"
assert_eq "create sub1 http_code" "$code" "200"
SUB1_ID="$(json_get "$sub1_json" id)"
assert_nonempty "sub1.id" "$SUB1_ID"

sub2_json="${OUT_DIR}/sub2_create.json"
code="$(
  curl -sS -o "$sub2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"SUB-S2-${ts}\",\"name\":\"Substitute 2\"}}"
)"
assert_eq "create sub2 http_code" "$code" "200"
SUB2_ID="$(json_get "$sub2_json" id)"
assert_nonempty "sub2.id" "$SUB2_ID"

log "Create BOM line (parent -> child)"
bom_json="${OUT_DIR}/bom_add_child.json"
code="$(
  curl -sS -o "$bom_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "create BOM line http_code" "$code" "200"
BOM_LINE_ID="$(json_get "$bom_json" relationship_id)"
assert_nonempty "bom.relationship_id" "$BOM_LINE_ID"

log "Add substitute 1"
add1_json="${OUT_DIR}/substitute_add_1.json"
code="$(
  curl -sS -o "$add1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${BOM_LINE_ID}/substitutes" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"${SUB1_ID}\",\"properties\":{\"rank\":1,\"note\":\"alt-1\"}}"
)"
assert_eq "add substitute 1 http_code" "$code" "200"
SUB_REL_1_ID="$(json_get "$add1_json" substitute_id)"
assert_nonempty "substitute_1.substitute_id" "$SUB_REL_1_ID"

log "List substitutes (expect 1)"
list1_json="${OUT_DIR}/substitutes_list_1.json"
code="$(
  curl -sS -o "$list1_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${BOM_LINE_ID}/substitutes" "${admin_header[@]}"
)"
assert_eq "list substitutes #1 http_code" "$code" "200"
assert_eq "list substitutes #1 count" "$(json_get "$list1_json" count)" "1"

log "Add substitute 2"
add2_json="${OUT_DIR}/substitute_add_2.json"
code="$(
  curl -sS -o "$add2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${BOM_LINE_ID}/substitutes" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"${SUB2_ID}\",\"properties\":{\"rank\":2}}"
)"
assert_eq "add substitute 2 http_code" "$code" "200"
SUB_REL_2_ID="$(json_get "$add2_json" substitute_id)"
assert_nonempty "substitute_2.substitute_id" "$SUB_REL_2_ID"

log "Duplicate add (should 400)"
dup_json="${OUT_DIR}/substitute_dup_add.json"
code="$(
  curl -sS -o "$dup_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${BOM_LINE_ID}/substitutes" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"${SUB2_ID}\"}"
)"
assert_eq "duplicate add http_code" "$code" "400"

log "Remove substitute 1"
del1_json="${OUT_DIR}/substitute_delete_1.json"
code="$(
  curl -sS -o "$del1_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/bom/${BOM_LINE_ID}/substitutes/${SUB_REL_1_ID}" \
    "${admin_header[@]}"
)"
assert_eq "delete substitute 1 http_code" "$code" "200"
assert_eq "delete substitute 1 ok" "$(json_get "$del1_json" ok)" "True"

log "List substitutes (expect 1 remaining)"
list2_json="${OUT_DIR}/substitutes_list_2.json"
code="$(
  curl -sS -o "$list2_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${BOM_LINE_ID}/substitutes" "${admin_header[@]}"
)"
assert_eq "list substitutes #2 http_code" "$code" "200"
assert_eq "list substitutes #2 count" "$(json_get "$list2_json" count)" "1"

log "PASS: BOM substitutes E2E verification"

