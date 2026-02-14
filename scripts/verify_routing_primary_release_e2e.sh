#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade, API-only verification for Manufacturing Routing primary switch + release.
#
# Coverage:
# - build a minimal EBOM (parent -> child) and create MBOM
# - create two routings in the same MBOM scope and validate primary uniqueness behavior
# - switch primary routing via: PUT /api/v1/routings/{routing_id}/primary
# - release-diagnostics + release guardrails:
#   - empty operations -> release-diagnostics errors + release blocked
#   - inactive workcenter referenced by an operation -> release-diagnostics errors + release blocked
# - successful routing release + already-released guardrail
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB + local storage, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-routing-primary-release/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_routing_primary_release_${timestamp}.db}"
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
WC_CODE="WC-${ts}"

log "Create EBOM parent + child"
parent_json="${OUT_DIR}/parent_create.json"
code="$(
  curl -sS -o "$parent_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"RPR-P-${ts}\",\"name\":\"Routing Release Parent\"}}"
)"
assert_eq "create parent http_code" "$code" "200"
PARENT_ID="$(json_get "$parent_json" id)"
assert_nonempty "parent.id" "$PARENT_ID"

child_json="${OUT_DIR}/child_create.json"
code="$(
  curl -sS -o "$child_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/aml/apply" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"RPR-C-${ts}\",\"name\":\"Routing Release Child\"}}"
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
    -d "{\"source_item_id\":\"${PARENT_ID}\",\"name\":\"MBOM-RPR-${ts}\"}"
)"
assert_eq "mbom create http_code" "$code" "200"
MBOM_ID="$(json_get "$mbom_create_json" id)"
assert_nonempty "mbom.id" "$MBOM_ID"

log "Create two routings (primary uniqueness contract)"
routing_a_json="${OUT_DIR}/routing_a_create.json"
code="$(
  curl -sS -o "$routing_a_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"Routing-A-${ts}\",\"mbom_id\":\"${MBOM_ID}\",\"plant_code\":\"${PLANT}\",\"line_code\":\"${LINE}\"}"
)"
assert_eq "routing A create http_code" "$code" "200"
ROUTING_A_ID="$(json_get "$routing_a_json" id)"
assert_nonempty "routing_a.id" "$ROUTING_A_ID"

routing_b_json="${OUT_DIR}/routing_b_create.json"
code="$(
  curl -sS -o "$routing_b_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"name\":\"Routing-B-${ts}\",\"mbom_id\":\"${MBOM_ID}\",\"plant_code\":\"${PLANT}\",\"line_code\":\"${LINE}\"}"
)"
assert_eq "routing B create http_code" "$code" "200"
ROUTING_B_ID="$(json_get "$routing_b_json" id)"
assert_nonempty "routing_b.id" "$ROUTING_B_ID"

log "Get routings and verify primary moved to the latest one"
routing_a_get1="${OUT_DIR}/routing_a_get_after_b.json"
code="$(
  curl -sS -o "$routing_a_get1" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}" \
    "${admin_header[@]}"
)"
assert_eq "routing A get http_code" "$code" "200"
assert_eq "routing A is_primary after B" "$(json_get "$routing_a_get1" is_primary)" "False"

routing_b_get1="${OUT_DIR}/routing_b_get.json"
code="$(
  curl -sS -o "$routing_b_get1" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_B_ID}" \
    "${admin_header[@]}"
)"
assert_eq "routing B get http_code" "$code" "200"
assert_eq "routing B is_primary" "$(json_get "$routing_b_get1" is_primary)" "True"

log "Switch primary back to routing A via PUT /primary"
routing_primary_json="${OUT_DIR}/routing_set_primary.json"
code="$(
  curl -sS -o "$routing_primary_json" -w "%{http_code}" \
    -X PUT "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/primary" \
    "${admin_header[@]}"
)"
assert_eq "set primary http_code" "$code" "200"
assert_eq "set primary response is_primary" "$(json_get "$routing_primary_json" is_primary)" "True"

routing_b_get2="${OUT_DIR}/routing_b_get_after_primary_switch.json"
code="$(
  curl -sS -o "$routing_b_get2" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_B_ID}" \
    "${admin_header[@]}"
)"
assert_eq "routing B get after switch http_code" "$code" "200"
assert_eq "routing B is_primary after switch" "$(json_get "$routing_b_get2" is_primary)" "False"

log "Release diagnostics (expect error: routing_empty_operations)"
diag_empty_ops_json="${OUT_DIR}/routing_release_diag_empty_ops.json"
code="$(
  curl -sS -o "$diag_empty_ops_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release-diagnostics?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release diagnostics (empty ops) http_code" "$code" "200"
"$PY_BIN" - "$diag_empty_ops_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
if resp.get("ok") is True:
  raise SystemExit("expected ok=false for empty operations")
codes = [e.get("code") for e in (resp.get("errors") or [])]
if "routing_empty_operations" not in codes:
  raise SystemExit(f"expected routing_empty_operations in errors, got: {codes}")
print("routing_release_diag_empty_ops_ok=1")
PY

log "Release routing (expect blocked; HTTP 400)"
release_empty_err_json="${OUT_DIR}/routing_release_empty_ops_err.json"
code="$(
  curl -sS -o "$release_empty_err_json" -w "%{http_code}" \
    -X PUT "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release (empty ops) http_code" "$code" "400"
"$PY_BIN" - "$release_empty_err_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
detail = str(resp.get("detail") or "")
if "operation" not in detail.lower():
  raise SystemExit(f"unexpected detail: {detail}")
print("routing_release_empty_ops_block_ok=1")
PY

log "Create workcenter and add an operation referencing it"
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

op1_json="${OUT_DIR}/op10_add.json"
code="$(
  curl -sS -o "$op1_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/operations" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"operation_number\":\"10\",\"name\":\"Cut\",\"workcenter_code\":\"${WC_CODE}\",\"setup_time\":5,\"run_time\":1}"
)"
assert_eq "add op10 http_code" "$code" "200"
assert_eq "op10.workcenter_code" "$(json_get "$op1_json" workcenter_code)" "$WC_CODE"
assert_nonempty "op10.workcenter_id" "$(json_get "$op1_json" workcenter_id)"

log "Deactivate workcenter -> release should be blocked by workcenter_inactive"
wc_deactivate_json="${OUT_DIR}/workcenter_deactivate.json"
code="$(
  curl -sS -o "$wc_deactivate_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/workcenters/${WC_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"is_active\":false}"
)"
assert_eq "workcenter deactivate http_code" "$code" "200"

diag_inactive_wc_json="${OUT_DIR}/routing_release_diag_inactive_workcenter.json"
code="$(
  curl -sS -o "$diag_inactive_wc_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release-diagnostics?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release diagnostics (inactive wc) http_code" "$code" "200"
"$PY_BIN" - "$diag_inactive_wc_json" "$WC_CODE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
if resp.get("ok") is True:
  raise SystemExit("expected ok=false for inactive workcenter")
codes = [e.get("code") for e in (resp.get("errors") or [])]
if "workcenter_inactive" not in codes:
  raise SystemExit(f"expected workcenter_inactive in errors, got: {codes}")
msgs = [str(e.get("message") or "") for e in (resp.get("errors") or [])]
if not any(sys.argv[2] in m for m in msgs):
  raise SystemExit(f"expected workcenter code {sys.argv[2]} in messages, got: {msgs}")
print("routing_release_diag_inactive_wc_ok=1")
PY

release_inactive_err_json="${OUT_DIR}/routing_release_inactive_workcenter_err.json"
code="$(
  curl -sS -o "$release_inactive_err_json" -w "%{http_code}" \
    -X PUT "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release (inactive wc) http_code" "$code" "400"
"$PY_BIN" - "$release_inactive_err_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
detail = str(resp.get("detail") or "")
if "inactive" not in detail.lower():
  raise SystemExit(f"unexpected detail: {detail}")
print("routing_release_inactive_wc_block_ok=1")
PY

log "Reactivate workcenter -> diagnostics ok -> release ok"
wc_reactivate_json="${OUT_DIR}/workcenter_reactivate.json"
code="$(
  curl -sS -o "$wc_reactivate_json" -w "%{http_code}" \
    -X PATCH "${BASE_URL}/api/v1/workcenters/${WC_ID}" \
    "${admin_header[@]}" -H 'content-type: application/json' \
    -d "{\"is_active\":true}"
)"
assert_eq "workcenter reactivate http_code" "$code" "200"

diag_ok_json="${OUT_DIR}/routing_release_diag_ok.json"
code="$(
  curl -sS -o "$diag_ok_json" -w "%{http_code}" \
    "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release-diagnostics?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release diagnostics (ok) http_code" "$code" "200"
"$PY_BIN" - "$diag_ok_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
if resp.get("ok") is not True:
  raise SystemExit(f"expected ok=true, got ok={resp.get('ok')}")
errors = resp.get("errors") or []
if errors:
  raise SystemExit(f"expected no errors, got: {[e.get('code') for e in errors]}")
print("routing_release_diag_ok=1")
PY

release_ok_json="${OUT_DIR}/routing_release_ok.json"
code="$(
  curl -sS -o "$release_ok_json" -w "%{http_code}" \
    -X PUT "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release ok http_code" "$code" "200"
assert_eq "routing.state after release" "$(json_get "$release_ok_json" state)" "released"

log "Release already-released routing (expect blocked; HTTP 400)"
release_again_err_json="${OUT_DIR}/routing_release_again_err.json"
code="$(
  curl -sS -o "$release_again_err_json" -w "%{http_code}" \
    -X PUT "${BASE_URL}/api/v1/routings/${ROUTING_A_ID}/release?ruleset_id=default" \
    "${admin_header[@]}"
)"
assert_eq "release again http_code" "$code" "400"
"$PY_BIN" - "$release_again_err_json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  resp = json.load(f)
detail = str(resp.get("detail") or "")
if "already" not in detail.lower():
  raise SystemExit(f"unexpected detail: {detail}")
print("routing_release_already_released_block_ok=1")
PY

log "PASS: Routing primary + release API E2E verification"

