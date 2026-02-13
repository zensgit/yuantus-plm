#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Baseline snapshots + compare.
#
# Coverage:
# - create a parent + children and build an initial BOM
# - create baseline snapshot and validate counts/shape
# - compare baseline vs current (no diff)
# - modify BOM (qty change + added line) and compare again (expect diff)
# - create a second baseline and compare baseline-to-baseline (expect diff)
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-baseline/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_baseline_${timestamp}.db}"
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

log "Create parent + children"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-A-${ts}\",\"name\":\"Baseline Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_b_json="${OUT_DIR}/child_b_create.json"
code="$(
  curl -sS -o "$child_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-B-${ts}\",\"name\":\"Child B\"}}"
)"
assert_eq "create child B http_code" "$code" "200"
CHILD_B_ID="$(json_get "$child_b_json" id)"
assert_nonempty "child_b.id" "$CHILD_B_ID"

child_c_json="${OUT_DIR}/child_c_create.json"
code="$(
  curl -sS -o "$child_c_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-C-${ts}\",\"name\":\"Child C\"}}"
)"
assert_eq "create child C http_code" "$code" "200"
CHILD_C_ID="$(json_get "$child_c_json" id)"
assert_nonempty "child_c.id" "$CHILD_C_ID"

log "Build BOM (parent -> B,C)"
add_b_json="${OUT_DIR}/bom_add_child_b.json"
code="$(
  curl -sS -o "$add_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_B_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add parent->B http_code" "$code" "200"
assert_eq "add parent->B ok" "$(json_get "$add_b_json" ok)" "True"

add_c_json="${OUT_DIR}/bom_add_child_c.json"
code="$(
  curl -sS -o "$add_c_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_C_ID}\",\"quantity\":2,\"uom\":\"EA\"}"
)"
assert_eq "add parent->C http_code" "$code" "200"
assert_eq "add parent->C ok" "$(json_get "$add_c_json" ok)" "True"

log "Create baseline (expect snapshot contains 2 children)"
baseline_create_json="${OUT_DIR}/baseline_create.json"
code="$(
  curl -sS -o "$baseline_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/baselines" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"BL-${ts}\",\"description\":\"Baseline test\",\"root_item_id\":\"${PARENT_ID}\",\"max_levels\":10}"
)"
assert_eq "baseline create http_code" "$code" "200"
BASELINE_ID="$(json_get "$baseline_create_json" id)"
assert_nonempty "baseline.id" "$BASELINE_ID"
"$PY_BIN" - "$baseline_create_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)

assert (resp.get("item_count") or 0) >= 3, resp
assert (resp.get("relationship_count") or 0) >= 2, resp

snap = resp.get("snapshot") or {}
children = snap.get("children") or []
assert len(children) == 2, children

print("baseline_snapshot_ok=1")
PY

log "Compare baseline vs current (expect no diffs)"
baseline_compare_nodiff_json="${OUT_DIR}/baseline_compare_no_diff.json"
code="$(
  curl -sS -o "$baseline_compare_nodiff_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/baselines/${BASELINE_ID}/compare" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"target_type\":\"item\",\"target_id\":\"${PARENT_ID}\",\"max_levels\":10}"
)"
assert_eq "baseline compare (no diff) http_code" "$code" "200"
"$PY_BIN" - "$baseline_compare_nodiff_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
summary = resp.get("summary") or {}
assert (summary.get("added") or 0) == 0, summary
assert (summary.get("removed") or 0) == 0, summary
assert (summary.get("changed") or 0) == 0, summary
print("baseline_compare_nodiff_ok=1")
PY

log "Modify BOM (change qty for B + add new child D)"
child_d_json="${OUT_DIR}/child_d_create.json"
code="$(
  curl -sS -o "$child_d_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"BL-D-${ts}\",\"name\":\"Child D\"}}"
)"
assert_eq "create child D http_code" "$code" "200"
CHILD_D_ID="$(json_get "$child_d_json" id)"
assert_nonempty "child_d.id" "$CHILD_D_ID"

rm_b_json="${OUT_DIR}/bom_remove_child_b.json"
code="$(
  curl -sS -o "$rm_b_json" -w "%{http_code}" \
    -X DELETE "${BASE_URL}/api/v1/bom/${PARENT_ID}/children/${CHILD_B_ID}" \
    "${admin_header[@]}"
)"
assert_eq "remove parent->B http_code" "$code" "200"

add_b2_json="${OUT_DIR}/bom_add_child_b_qty3.json"
code="$(
  curl -sS -o "$add_b2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_B_ID}\",\"quantity\":3,\"uom\":\"EA\"}"
)"
assert_eq "re-add parent->B qty=3 http_code" "$code" "200"
assert_eq "re-add parent->B ok" "$(json_get "$add_b2_json" ok)" "True"

add_d_json="${OUT_DIR}/bom_add_child_d.json"
code="$(
  curl -sS -o "$add_d_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/bom/${PARENT_ID}/children" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"child_id\":\"${CHILD_D_ID}\",\"quantity\":1,\"uom\":\"EA\"}"
)"
assert_eq "add parent->D http_code" "$code" "200"
assert_eq "add parent->D ok" "$(json_get "$add_d_json" ok)" "True"

log "Compare baseline vs current (expect added + changed)"
baseline_compare_diff_json="${OUT_DIR}/baseline_compare_diff.json"
code="$(
  curl -sS -o "$baseline_compare_diff_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/baselines/${BASELINE_ID}/compare" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"target_type\":\"item\",\"target_id\":\"${PARENT_ID}\",\"max_levels\":10}"
)"
assert_eq "baseline compare (diff) http_code" "$code" "200"
"$PY_BIN" - "$baseline_compare_diff_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
summary = resp.get("summary") or {}
added = int(summary.get("added") or 0)
changed = int(summary.get("changed") or 0)
assert added >= 1, summary
assert changed >= 1, summary
print("baseline_compare_diff_ok=1")
PY

log "Create baseline #2 and compare baseline-to-baseline (expect diff)"
baseline2_create_json="${OUT_DIR}/baseline2_create.json"
code="$(
  curl -sS -o "$baseline2_create_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/baselines" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"BL2-${ts}\",\"root_item_id\":\"${PARENT_ID}\",\"max_levels\":10}"
)"
assert_eq "baseline2 create http_code" "$code" "200"
BASELINE2_ID="$(json_get "$baseline2_create_json" id)"
assert_nonempty "baseline2.id" "$BASELINE2_ID"

baseline_compare_b2_json="${OUT_DIR}/baseline_compare_baseline.json"
code="$(
  curl -sS -o "$baseline_compare_b2_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/baselines/${BASELINE_ID}/compare" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"target_type\":\"baseline\",\"target_id\":\"${BASELINE2_ID}\",\"max_levels\":10}"
)"
assert_eq "baseline compare baseline http_code" "$code" "200"
"$PY_BIN" - "$baseline_compare_b2_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
summary = resp.get("summary") or {}
assert int(summary.get("added") or 0) >= 1, summary
assert int(summary.get("changed") or 0) >= 1, summary
print("baseline_compare_baseline_ok=1")
PY

log "PASS: Baseline API E2E verification"

