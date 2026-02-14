#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for BOM weight rollup.
#
# Coverage:
# - rollup totals match sum(child_weight * qty)
# - write_back updates parent property when missing
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-bom-weight-rollup/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_bom_weight_rollup_${timestamp}.db}"
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

log "Create Parts (parent without weight; two children with weights)"
parent_json="${OUT_DIR}/part_parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ROLLUP-P-${ts}\",\"name\":\"Rollup Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child1_json="${OUT_DIR}/part_child1_create.json"
code="$(
  curl -sS -o "$child1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ROLLUP-C1-${ts}\",\"name\":\"Child 1\",\"weight\":2.5}}"
)"
assert_eq "create child1 http_code" "$code" "200"
CHILD1_ID="$(json_get "$child1_json" id)"
assert_nonempty "child1.id" "$CHILD1_ID"

child2_json="${OUT_DIR}/part_child2_create.json"
code="$(
  curl -sS -o "$child2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"ROLLUP-C2-${ts}\",\"name\":\"Child 2\",\"weight\":1.0}}"
)"
assert_eq "create child2 http_code" "$code" "200"
CHILD2_ID="$(json_get "$child2_json" id)"
assert_nonempty "child2.id" "$CHILD2_ID"

log "Build BOM: parent -> (child1 qty=2, child2 qty=3)"
bom_add_1_json="${OUT_DIR}/bom_add_child1.json"
code="$(
  curl -sS -o "$bom_add_1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD1_ID}\",\"quantity\":2}"
)"
assert_eq "add child1 http_code" "$code" "200"
assert_eq "add child1 ok" "$(json_get "$bom_add_1_json" ok)" "True"

bom_add_2_json="${OUT_DIR}/bom_add_child2.json"
code="$(
  curl -sS -o "$bom_add_2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD2_ID}\",\"quantity\":3}"
)"
assert_eq "add child2 http_code" "$code" "200"
assert_eq "add child2 ok" "$(json_get "$bom_add_2_json" ok)" "True"

log "Rollup weight (write_back=missing, rounding=3; expect total_weight=8.0)"
rollup_json="${OUT_DIR}/rollup_weight.json"
code="$(
  curl -sS -o "$rollup_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/rollup/weight" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d '{"write_back":true,"write_back_field":"weight_rollup","write_back_mode":"missing","rounding":3}'
)"
assert_eq "rollup weight http_code" "$code" "200"
"$PY_BIN" - "$rollup_json" <<'PY'
import json
import math
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
total = float(((resp.get("summary") or {}).get("total_weight")) or 0)
expected = 8.0
if not math.isclose(total, expected, rel_tol=1e-9, abs_tol=1e-9):
  raise SystemExit(f"expected total_weight={expected}, got {total}")
print("bom_weight_rollup_total_ok=1")
PY

log "Verify write_back (parent.weight_rollup == 8.0)"
aml_get_json="${OUT_DIR}/aml_get_parent.json"
code="$(
  curl -sS -o "$aml_get_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"get\",\"id\":\"${PARENT_ID}\"}"
)"
assert_eq "aml get parent http_code" "$code" "200"
"$PY_BIN" - "$aml_get_json" <<'PY'
import json
import math
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
items = resp.get("items") or []
if not items:
  raise SystemExit("expected items[0]")
props = (items[0] or {}).get("properties") or {}
val = props.get("weight_rollup")
if val is None:
  raise SystemExit("expected properties.weight_rollup present")
got = float(val)
expected = 8.0
if not math.isclose(got, expected, rel_tol=1e-9, abs_tol=1e-9):
  raise SystemExit(f"expected weight_rollup={expected}, got {got}")
print("bom_weight_rollup_write_back_ok=1")
PY

log "PASS: BOM weight rollup API E2E verification"

