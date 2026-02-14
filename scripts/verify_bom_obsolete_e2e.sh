#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for BOM obsolete scan + resolve.
#
# Coverage:
# - obsolete scan detects obsolete child lines and reports replacement_id
# - resolve mode "update": swaps child line to replacement_id (in-place)
# - resolve mode "new_bom": clones lines and swaps child to replacement_id
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-bom-obsolete/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_bom_obsolete_${timestamp}.db}"
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

create_part() {
  local out="$1"
  local number="$2"
  local name="$3"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/aml/apply" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${number}\",\"name\":\"${name}\"}}"
  )"
  [[ "$http_code" == "200" ]] || fail "create part ${number} -> HTTP ${http_code} (out=${out})"
  json_get "$out" id
}

mark_obsolete() {
  local out="$1"
  local item_id="$2"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/aml/apply" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"${item_id}\",\"properties\":{\"engineering_state\":\"obsoleted\",\"obsolete\":true}}"
  )"
  [[ "$http_code" == "200" ]] || fail "mark obsolete -> HTTP ${http_code} (out=${out})"
}

set_replacement() {
  local out="$1"
  local item_id="$2"
  local replacement_id="$3"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/aml/apply" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"type\":\"Part\",\"action\":\"update\",\"id\":\"${item_id}\",\"properties\":{\"replacement_id\":\"${replacement_id}\"}}"
  )"
  [[ "$http_code" == "200" ]] || fail "set replacement -> HTTP ${http_code} (out=${out})"
}

add_bom_child() {
  local out="$1"
  local parent_id="$2"
  local child_id="$3"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/bom/${parent_id}/children" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"child_id\":\"${child_id}\",\"quantity\":1}"
  )"
  [[ "$http_code" == "200" ]] || fail "add bom child -> HTTP ${http_code} (out=${out})"
  assert_eq "add bom child ok" "$(json_get "$out" ok)" "True"
}

scan_obsolete() {
  local out="$1"
  local parent_id="$2"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      "${BASE_URL}/api/v1/bom/${parent_id}/obsolete" \
      "${admin_header[@]}"
  )"
  [[ "$http_code" == "200" ]] || fail "obsolete scan -> HTTP ${http_code} (out=${out})"
}

resolve_obsolete() {
  local out="$1"
  local parent_id="$2"
  local mode="$3"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/bom/${parent_id}/obsolete/resolve" \
      "${admin_header[@]}" -H 'content-type: application/json' \
      -d "{\"mode\":\"${mode}\"}"
  )"
  [[ "$http_code" == "200" ]] || fail "obsolete resolve (${mode}) -> HTTP ${http_code} (out=${out})"
}

get_bom_tree_1() {
  local out="$1"
  local parent_id="$2"
  local http_code
  http_code="$(
    curl -sS -o "$out" -w "%{http_code}" \
      "${BASE_URL}/api/v1/bom/${parent_id}/tree?depth=1" \
      "${admin_header[@]}"
  )"
  [[ "$http_code" == "200" ]] || fail "bom tree -> HTTP ${http_code} (out=${out})"
}

log "Case 1: resolve mode=update"
PARENT_1="$(create_part "${OUT_DIR}/part_parent_1.json" "OBS-PARENT-${ts}" "Obsolete Parent")"
CHILD_OLD="$(create_part "${OUT_DIR}/part_child_old.json" "OBS-OLD-${ts}" "Obsolete Child")"
CHILD_NEW="$(create_part "${OUT_DIR}/part_child_new.json" "OBS-NEW-${ts}" "Replacement Child")"

mark_obsolete "${OUT_DIR}/part_child_old_obsolete.json" "$CHILD_OLD"
set_replacement "${OUT_DIR}/part_child_old_replacement.json" "$CHILD_OLD" "$CHILD_NEW"
add_bom_child "${OUT_DIR}/bom_add_child_old.json" "$PARENT_1" "$CHILD_OLD"

scan_obsolete "${OUT_DIR}/obsolete_scan_before_update.json" "$PARENT_1"
assert_eq "obsolete scan count before update" "$(json_get "${OUT_DIR}/obsolete_scan_before_update.json" count)" "1"
"$PY_BIN" - "${OUT_DIR}/obsolete_scan_before_update.json" "$CHILD_NEW" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
entries = resp.get("entries") or []
if not entries:
  raise SystemExit("expected at least 1 entry")
replacement_id = (entries[0] or {}).get("replacement_id")
if str(replacement_id) != sys.argv[2]:
  raise SystemExit(f"expected replacement_id={sys.argv[2]}, got {replacement_id}")
print("obsolete_scan_replacement_ok=1")
PY

resolve_obsolete "${OUT_DIR}/obsolete_resolve_update.json" "$PARENT_1" "update"
assert_eq "resolve(update) updated_lines" "$(json_get "${OUT_DIR}/obsolete_resolve_update.json" summary.updated_lines)" "1"

scan_obsolete "${OUT_DIR}/obsolete_scan_after_update.json" "$PARENT_1"
assert_eq "obsolete scan count after update" "$(json_get "${OUT_DIR}/obsolete_scan_after_update.json" count)" "0"

get_bom_tree_1 "${OUT_DIR}/bom_tree_after_update.json" "$PARENT_1"
"$PY_BIN" - "${OUT_DIR}/bom_tree_after_update.json" "$CHILD_NEW" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  tree = json.load(f)
children = tree.get("children") or []
if not children:
  raise SystemExit("expected at least 1 child")
child_id = ((children[0] or {}).get("child") or {}).get("id")
if str(child_id) != sys.argv[2]:
  raise SystemExit(f"expected child.id={sys.argv[2]}, got {child_id}")
print("obsolete_update_child_ok=1")
PY

log "Case 2: resolve mode=new_bom"
PARENT_2="$(create_part "${OUT_DIR}/part_parent_2.json" "OBS-PARENT2-${ts}" "Obsolete Parent 2")"
CHILD_OLD2="$(create_part "${OUT_DIR}/part_child_old2.json" "OBS-OLD2-${ts}" "Obsolete Child 2")"
CHILD_NEW2="$(create_part "${OUT_DIR}/part_child_new2.json" "OBS-NEW2-${ts}" "Replacement Child 2")"

mark_obsolete "${OUT_DIR}/part_child_old2_obsolete.json" "$CHILD_OLD2"
set_replacement "${OUT_DIR}/part_child_old2_replacement.json" "$CHILD_OLD2" "$CHILD_NEW2"
add_bom_child "${OUT_DIR}/bom_add_child_old2.json" "$PARENT_2" "$CHILD_OLD2"

scan_obsolete "${OUT_DIR}/obsolete_scan_before_new_bom.json" "$PARENT_2"
assert_eq "obsolete scan count before new_bom" "$(json_get "${OUT_DIR}/obsolete_scan_before_new_bom.json" count)" "1"

resolve_obsolete "${OUT_DIR}/obsolete_resolve_new_bom.json" "$PARENT_2" "new_bom"
assert_eq "resolve(new_bom) updated_lines" "$(json_get "${OUT_DIR}/obsolete_resolve_new_bom.json" summary.updated_lines)" "1"

scan_obsolete "${OUT_DIR}/obsolete_scan_after_new_bom.json" "$PARENT_2"
assert_eq "obsolete scan count after new_bom" "$(json_get "${OUT_DIR}/obsolete_scan_after_new_bom.json" count)" "0"

get_bom_tree_1 "${OUT_DIR}/bom_tree_after_new_bom.json" "$PARENT_2"
"$PY_BIN" - "${OUT_DIR}/bom_tree_after_new_bom.json" "$CHILD_NEW2" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  tree = json.load(f)
children = tree.get("children") or []
if not children:
  raise SystemExit("expected at least 1 child")
child_id = ((children[0] or {}).get("child") or {}).get("id")
if str(child_id) != sys.argv[2]:
  raise SystemExit(f"expected child.id={sys.argv[2]}, got {child_id}")
print("obsolete_new_bom_child_ok=1")
PY

log "PASS: BOM obsolete scan + resolve API E2E verification"

