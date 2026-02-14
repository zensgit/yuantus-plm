#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Effectivity Extended (Lot/Serial).
#
# Coverage:
# - build a minimal BOM (parent -> child_lot, child_serial)
# - create Lot/Serial effectivities on BOM relationship lines via POST /api/v1/effectivities
# - query effective BOM with matching vs non-matching lot/serial inputs
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-effectivity-extended/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_effectivity_extended_${timestamp}.db}"
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

log "Create Parts (parent + lot child + serial child)"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EFFX-${ts}-P\",\"name\":\"EffX Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_lot_json="${OUT_DIR}/child_lot_create.json"
code="$(
  curl -sS -o "$child_lot_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EFFX-${ts}-L\",\"name\":\"EffX Lot Child\"}}"
)"
assert_eq "create lot child http_code" "$code" "200"
CHILD_LOT_ID="$(json_get "$child_lot_json" id)"
assert_nonempty "child_lot.id" "$CHILD_LOT_ID"

child_serial_json="${OUT_DIR}/child_serial_create.json"
code="$(
  curl -sS -o "$child_serial_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"EFFX-${ts}-S\",\"name\":\"EffX Serial Child\"}}"
)"
assert_eq "create serial child http_code" "$code" "200"
CHILD_SERIAL_ID="$(json_get "$child_serial_json" id)"
assert_nonempty "child_serial.id" "$CHILD_SERIAL_ID"

log "Add BOM children (expect ok=true + relationship_id)"
bom_add_lot_json="${OUT_DIR}/bom_add_lot.json"
code="$(
  curl -sS -o "$bom_add_lot_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_LOT_ID}\",\"quantity\":1}"
)"
assert_eq "add lot child http_code" "$code" "200"
assert_eq "add lot child ok" "$(json_get "$bom_add_lot_json" ok)" "True"
REL_LOT_ID="$(json_get "$bom_add_lot_json" relationship_id)"
assert_nonempty "rel_lot.id" "$REL_LOT_ID"

bom_add_serial_json="${OUT_DIR}/bom_add_serial.json"
code="$(
  curl -sS -o "$bom_add_serial_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_SERIAL_ID}\",\"quantity\":1}"
)"
assert_eq "add serial child http_code" "$code" "200"
assert_eq "add serial child ok" "$(json_get "$bom_add_serial_json" ok)" "True"
REL_SERIAL_ID="$(json_get "$bom_add_serial_json" relationship_id)"
assert_nonempty "rel_serial.id" "$REL_SERIAL_ID"

log "Create Lot effectivity on relationship line"
lot_eff_json="${OUT_DIR}/effectivity_lot_create.json"
code="$(
  curl -sS -o "$lot_eff_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/effectivities" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"item_id\":\"${REL_LOT_ID}\",\"effectivity_type\":\"Lot\",\"payload\":{\"lot_start\":\"L010\",\"lot_end\":\"L020\"}}"
)"
assert_eq "create lot effectivity http_code" "$code" "200"
LOT_EFF_ID="$(json_get "$lot_eff_json" id)"
assert_nonempty "lot_effectivity.id" "$LOT_EFF_ID"

log "Create Serial effectivity on relationship line"
serial_eff_json="${OUT_DIR}/effectivity_serial_create.json"
code="$(
  curl -sS -o "$serial_eff_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/effectivities" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"item_id\":\"${REL_SERIAL_ID}\",\"effectivity_type\":\"Serial\",\"payload\":{\"serials\":[\"SN-1\",\"SN-2\"]}}"
)"
assert_eq "create serial effectivity http_code" "$code" "200"
SERIAL_EFF_ID="$(json_get "$serial_eff_json" id)"
assert_nonempty "serial_effectivity.id" "$SERIAL_EFF_ID"

log "Query effective BOM with matching lot+serial (expect both children visible)"
eff_match_json="${OUT_DIR}/effective_bom_match.json"
code="$(
  curl -sS -o "$eff_match_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PARENT_ID}/effective?lot_number=L015&serial_number=SN-1&levels=1" \
    "${admin_header[@]}"
)"
assert_eq "effective bom (match) http_code" "$code" "200"
"$PY_BIN" - "$eff_match_json" "$CHILD_LOT_ID" "$CHILD_SERIAL_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  tree = json.load(f)
children = tree.get("children") or []
ids = []
for c in children:
  child = (c or {}).get("child") or {}
  if child.get("id"):
    ids.append(str(child["id"]))

want = sorted([sys.argv[2], sys.argv[3]])
got = sorted(ids)
if got != want:
  raise SystemExit(f"expected children={want}, got={got}")
print("effectivity_extended_match_ok=1")
PY

log "Query effective BOM with non-matching lot+serial (expect no children)"
eff_nomatch_json="${OUT_DIR}/effective_bom_nomatch.json"
code="$(
  curl -sS -o "$eff_nomatch_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${PARENT_ID}/effective?lot_number=L030&serial_number=SN-9&levels=1" \
    "${admin_header[@]}"
)"
assert_eq "effective bom (nomatch) http_code" "$code" "200"
"$PY_BIN" - "$eff_nomatch_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  tree = json.load(f)
children = tree.get("children") or []
if len(children) != 0:
  raise SystemExit(f"expected 0 children, got {len(children)}")
print("effectivity_extended_nomatch_ok=1")
PY

log "PASS: Effectivity Extended (Lot/Serial) API E2E verification"

