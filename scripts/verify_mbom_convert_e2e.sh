#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for EBOM -> MBOM conversion.
#
# Coverage:
# - create EBOM parts + BOM line + substitute
# - convert EBOM -> MBOM via /api/v1/bom/convert/ebom-to-mbom
# - verify MBOM root exists (Manufacturing Part) and links back to EBOM root
# - verify MBOM tree endpoint returns expected child (source_ebom_id)
# - verify substitutes were copied to MBOM BOM line
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-mbom-convert/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_mbom_convert_${timestamp}.db}"
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

log "Create EBOM parts"
root_json="${OUT_DIR}/ebom_root_create.json"
code="$(
  curl -sS -o "$root_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-R-${ts}\",\"name\":\"EBOM Root\"}}"
)"
assert_eq "create EBOM root http_code" "$code" "200"
ROOT_ID="$(json_get "$root_json" id)"
assert_nonempty "ebom_root.id" "$ROOT_ID"

child_json="${OUT_DIR}/ebom_child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-C-${ts}\",\"name\":\"EBOM Child\"}}"
)"
assert_eq "create EBOM child http_code" "$code" "200"
CHILD_ID="$(json_get "$child_json" id)"
assert_nonempty "ebom_child.id" "$CHILD_ID"

sub_json="${OUT_DIR}/ebom_sub_create.json"
code="$(
  curl -sS -o "$sub_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"MBOM-S-${ts}\",\"name\":\"EBOM Substitute\"}}"
)"
assert_eq "create EBOM substitute http_code" "$code" "200"
SUB_ID="$(json_get "$sub_json" id)"
assert_nonempty "ebom_sub.id" "$SUB_ID"

log "Create EBOM BOM line"
bom_json="${OUT_DIR}/ebom_bom_add_child.json"
code="$(
  curl -sS -o "$bom_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${ROOT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_ID}\",\"quantity\":2,\"uom\":\"EA\"}"
)"
assert_eq "create EBOM BOM line http_code" "$code" "200"
BOM_REL_ID="$(json_get "$bom_json" relationship_id)"
assert_nonempty "ebom_bom.relationship_id" "$BOM_REL_ID"

log "Add substitute to EBOM BOM line"
sub_rel_json="${OUT_DIR}/ebom_substitute_add.json"
code="$(
  curl -sS -o "$sub_rel_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${BOM_REL_ID}/substitutes" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"substitute_item_id\":\"${SUB_ID}\",\"properties\":{\"rank\":1}}"
)"
assert_eq "add EBOM substitute http_code" "$code" "200"
SUB_REL_ID="$(json_get "$sub_rel_json" substitute_id)"
assert_nonempty "ebom_substitute.substitute_id" "$SUB_REL_ID"

log "Convert EBOM -> MBOM"
convert_json="${OUT_DIR}/mbom_convert.json"
code="$(
  curl -sS -o "$convert_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/convert/ebom-to-mbom" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"root_id\":\"${ROOT_ID}\"}"
)"
assert_eq "convert http_code" "$code" "200"
assert_eq "convert.ok" "$(json_get "$convert_json" ok)" "True"
MBOM_ROOT_ID="$(json_get "$convert_json" mbom_root_id)"
assert_nonempty "convert.mbom_root_id" "$MBOM_ROOT_ID"
assert_eq "convert.source_root_id" "$(json_get "$convert_json" source_root_id)" "$ROOT_ID"
assert_eq "convert.mbom_root_type" "$(json_get "$convert_json" mbom_root_type)" "Manufacturing Part"

log "Validate MBOM root via AML"
mbom_get_json="${OUT_DIR}/mbom_root_get.json"
code="$(
  curl -sS -o "$mbom_get_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Manufacturing Part\",\"action\":\"get\",\"id\":\"${MBOM_ROOT_ID}\"}"
)"
assert_eq "AML get MBOM root http_code" "$code" "200"
assert_eq "AML get MBOM root count" "$(json_get "$mbom_get_json" count)" "1"
"$PY_BIN" - "$mbom_get_json" "$ROOT_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
items = data.get("items") or []
props = (items[0] if items else {}).get("properties") or {}
if props.get("source_ebom_id") != sys.argv[2]:
  raise SystemExit("MBOM root missing/invalid source_ebom_id")
print("mbom_root_source_ok=1")
PY

log "Validate MBOM tree endpoint"
tree_json="${OUT_DIR}/mbom_tree_depth2.json"
code="$(
  curl -sS -o "$tree_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/mbom/${MBOM_ROOT_ID}/tree?depth=2" "${admin_header[@]}"
)"
assert_eq "MBOM tree http_code" "$code" "200"

MBOM_REL_ID="$("$PY_BIN" - "$tree_json" "$CHILD_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
expected_child_source = sys.argv[2]
children = data.get("children") or []
for entry in children:
  child = entry.get("child") or {}
  rel = entry.get("relationship") or {}
  if child.get("source_ebom_id") == expected_child_source:
    print(rel.get("id") or "")
    raise SystemExit(0)
print("")
PY
)"
assert_nonempty "mbom.relationship_id" "$MBOM_REL_ID"

log "Validate MBOM substitutes were copied"
mbom_subs_json="${OUT_DIR}/mbom_substitutes_list.json"
code="$(
  curl -sS -o "$mbom_subs_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/bom/${MBOM_REL_ID}/substitutes" "${admin_header[@]}"
)"
assert_eq "MBOM list substitutes http_code" "$code" "200"
assert_eq "MBOM substitutes count" "$(json_get "$mbom_subs_json" count)" "1"
"$PY_BIN" - "$mbom_subs_json" "$SUB_ID" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
expected_source = sys.argv[2]
items = data.get("substitutes") or []
if not items:
  raise SystemExit("expected substitutes list non-empty")
sub_part = (items[0] or {}).get("substitute_part") or {}
if sub_part.get("source_ebom_id") != expected_source:
  raise SystemExit("MBOM substitute missing/invalid source_ebom_id")
print("mbom_substitute_source_ok=1")
PY

log "PASS: MBOM convert E2E verification"

