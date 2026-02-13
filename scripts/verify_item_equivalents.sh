#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Item Equivalents.
#
# Coverage:
# - create Part A/B/C
# - add equivalents: A<->B, A<->C
# - list equivalents for A/B (expected counts + ids)
# - guardrails: duplicate add (400), self-equivalence (400)
# - remove equivalent relationship and verify list updates
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-item-equivalents/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_item_equivalents_${timestamp}.db}"
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

log "Create 3 parts"
ts="$(date +%s)"
part_a_json="${OUT_DIR}/part_a_create.json"
code="$(
  curl -sS -o "$part_a_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EQ-A-${ts}\",\"name\":\"Equivalent A\"}}"
)"
assert_eq "create part A http_code" "$code" "200"
PART_A_ID="$(json_get "$part_a_json" id)"
assert_nonempty "part_a.id" "$PART_A_ID"

part_b_json="${OUT_DIR}/part_b_create.json"
code="$(
  curl -sS -o "$part_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EQ-B-${ts}\",\"name\":\"Equivalent B\"}}"
)"
assert_eq "create part B http_code" "$code" "200"
PART_B_ID="$(json_get "$part_b_json" id)"
assert_nonempty "part_b.id" "$PART_B_ID"

part_c_json="${OUT_DIR}/part_c_create.json"
code="$(
  curl -sS -o "$part_c_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EQ-C-${ts}\",\"name\":\"Equivalent C\"}}"
)"
assert_eq "create part C http_code" "$code" "200"
PART_C_ID="$(json_get "$part_c_json" id)"
assert_nonempty "part_c.id" "$PART_C_ID"

log "Add equivalent A<->B"
add_ab_json="${OUT_DIR}/equivalent_add_ab.json"
code="$(
  curl -sS -o "$add_ab_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/items/${PART_A_ID}/equivalents" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"equivalent_item_id\":\"${PART_B_ID}\",\"properties\":{\"rank\":1,\"note\":\"primary\"}}"
)"
assert_eq "add A-B http_code" "$code" "200"
EQ_AB_ID="$(json_get "$add_ab_json" equivalent_id)"
assert_nonempty "equivalent_add_ab.equivalent_id" "$EQ_AB_ID"
assert_eq "equivalent_add_ab.item_id" "$(json_get "$add_ab_json" item_id)" "$PART_A_ID"
assert_eq "equivalent_add_ab.equivalent_item_id" "$(json_get "$add_ab_json" equivalent_item_id)" "$PART_B_ID"

log "Add equivalent A<->C"
add_ac_json="${OUT_DIR}/equivalent_add_ac.json"
code="$(
  curl -sS -o "$add_ac_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/items/${PART_A_ID}/equivalents" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"equivalent_item_id\":\"${PART_C_ID}\",\"properties\":{\"rank\":2}}"
)"
assert_eq "add A-C http_code" "$code" "200"
EQ_AC_ID="$(json_get "$add_ac_json" equivalent_id)"
assert_nonempty "equivalent_add_ac.equivalent_id" "$EQ_AC_ID"

log "List equivalents for A (expect 2: B,C)"
list_a_json="${OUT_DIR}/equivalents_list_a.json"
code="$(
  curl -sS -o "$list_a_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/items/${PART_A_ID}/equivalents" "${admin_header[@]}"
)"
assert_eq "list A http_code" "$code" "200"
assert_eq "list A count" "$(json_get "$list_a_json" count)" "2"
"$PY_BIN" - "$list_a_json" "$PART_B_ID" "$PART_C_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
ids = [e.get("equivalent_item_id") for e in (data.get("equivalents") or [])]
expect1, expect2 = sys.argv[2], sys.argv[3]
if expect1 not in ids or expect2 not in ids:
  raise SystemExit(f"expected A equivalents to include {expect1} and {expect2}, got {ids}")
print("equivalents_list_a_ok=1")
PY

log "List equivalents for B (expect 1: A)"
list_b_json="${OUT_DIR}/equivalents_list_b.json"
code="$(
  curl -sS -o "$list_b_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/items/${PART_B_ID}/equivalents" "${admin_header[@]}"
)"
assert_eq "list B http_code" "$code" "200"
assert_eq "list B count" "$(json_get "$list_b_json" count)" "1"
"$PY_BIN" - "$list_b_json" "$PART_A_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
ids = [e.get("equivalent_item_id") for e in (data.get("equivalents") or [])]
expect = sys.argv[2]
if expect not in ids:
  raise SystemExit(f"expected B equivalents to include {expect}, got {ids}")
print("equivalents_list_b_ok=1")
PY

log "Duplicate add (B -> A, expect 400)"
dup_json="${OUT_DIR}/equivalent_dup_add.json"
code="$(
  curl -sS -o "$dup_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/items/${PART_B_ID}/equivalents" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"equivalent_item_id\":\"${PART_A_ID}\"}"
)"
assert_eq "duplicate add http_code" "$code" "400"

log "Self-equivalence (A -> A, expect 400)"
self_json="${OUT_DIR}/equivalent_self_add.json"
code="$(
  curl -sS -o "$self_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/items/${PART_A_ID}/equivalents" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"equivalent_item_id\":\"${PART_A_ID}\"}"
)"
assert_eq "self add http_code" "$code" "400"

log "Remove equivalent A-B"
del_ab_json="${OUT_DIR}/equivalent_delete_ab.json"
code="$(
  curl -sS -o "$del_ab_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/items/${PART_A_ID}/equivalents/${EQ_AB_ID}" \
    "${admin_header[@]}"
)"
assert_eq "delete A-B http_code" "$code" "200"
assert_eq "delete A-B ok" "$(json_get "$del_ab_json" ok)" "True"
assert_eq "delete A-B equivalent_id" "$(json_get "$del_ab_json" equivalent_id)" "$EQ_AB_ID"

log "List equivalents for B (expect 0)"
list_b2_json="${OUT_DIR}/equivalents_list_b2.json"
code="$(
  curl -sS -o "$list_b2_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/items/${PART_B_ID}/equivalents" "${admin_header[@]}"
)"
assert_eq "list B2 http_code" "$code" "200"
assert_eq "list B2 count" "$(json_get "$list_b2_json" count)" "0"

log "List equivalents for A (expect 1)"
list_a2_json="${OUT_DIR}/equivalents_list_a2.json"
code="$(
  curl -sS -o "$list_a2_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/items/${PART_A_ID}/equivalents" "${admin_header[@]}"
)"
assert_eq "list A2 http_code" "$code" "200"
assert_eq "list A2 count" "$(json_get "$list_a2_json" count)" "1"

log "PASS: Item equivalents E2E verification"

