#!/usr/bin/env bash
set -euo pipefail

# Evidence-grade E2E verification for:
# - scripts/release_orchestration.sh login + plan/execute calls
# - release orchestration rollback behavior when baseline release is blocked by incomplete e-sign manifest
# - e-sign manifest completion via /api/v1/esign/sign
#
# This script is self-contained: it starts a temporary local server using a
# fresh SQLite DB, runs the scenario, and shuts the server down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-release-orchestration/${timestamp}"
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_release_orch_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

export PYTHONPATH="${PYTHONPATH:-src}"
# Force an isolated ephemeral DB for this verification, even if the caller has
# YUANTUS_* env vars set (e.g., running via scripts/verify_all.sh).
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

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

log "Login"
login_json="${OUT_DIR}/login.json"
code="$(
  curl -sS -o "$login_json" -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H 'content-type: application/json' \
    -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"
)"
if [[ "$code" != "200" ]]; then
  cat "$login_json" >&2 || true
  fail "login -> HTTP $code"
fi

TOKEN="$("$PY_BIN" - "$login_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"
if [[ -z "$TOKEN" ]]; then
  fail "failed to parse access_token"
fi

auth_header=(-H "Authorization: Bearer ${TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
json_header=(-H "content-type: application/json")

request_json() {
  local method="$1"
  local path="$2"
  local out_path="$3"
  local data="${4:-}"

  local url="${BASE_URL}${path}"
  local http_code
  if [[ -n "$data" ]]; then
    http_code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}" "${json_header[@]}" -d "$data")"
  else
    http_code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}")"
  fi

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    cat "$out_path" >&2 || true
    fail "${method} ${path} -> HTTP ${http_code} (out: ${out_path})"
  fi
}

json_id() {
  "$PY_BIN" - "$1" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
print(data.get("id") or "")
PY
}

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

ts="$(date +%s)"
parent_number="RELORCH-PARENT-${ts}"
child_number="RELORCH-CHILD-${ts}"

log "Create items + EBOM + baseline"
parent_json="${OUT_DIR}/part_parent.json"
request_json POST "/api/v1/aml/apply" "$parent_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${parent_number}\",\"name\":\"RelOrch Parent ${ts}\"}}"
parent_id="$(json_id "$parent_json")"
[[ -n "$parent_id" ]] || fail "failed to parse parent item id"

child_json="${OUT_DIR}/part_child.json"
request_json POST "/api/v1/aml/apply" "$child_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${child_number}\",\"name\":\"RelOrch Child ${ts}\"}}"
child_id="$(json_id "$child_json")"
[[ -n "$child_id" ]] || fail "failed to parse child item id"

request_json POST "/api/v1/bom/${parent_id}/children" "${OUT_DIR}/bom_add_child.json" \
  "{\"child_id\":\"${child_id}\",\"quantity\":1,\"uom\":\"EA\"}"

baseline_json="${OUT_DIR}/baseline_create.json"
request_json POST "/api/v1/baselines" "$baseline_json" \
  "{\"name\":\"RelOrch Baseline ${ts}\",\"root_item_id\":\"${parent_id}\",\"auto_populate\":true}"
baseline_id="$(json_id "$baseline_json")"
[[ -n "$baseline_id" ]] || fail "failed to parse baseline id"

baseline_diag_json="${OUT_DIR}/baseline_release_diagnostics.json"
request_json GET "/api/v1/baselines/${baseline_id}/release-diagnostics?ruleset_id=default" "$baseline_diag_json"
baseline_ok="$(json_get "$baseline_diag_json" ok)"
baseline_force="false"
if [[ "$baseline_ok" != "True" && "$baseline_ok" != "true" ]]; then
  baseline_force="true"
fi

log "Create manufacturing objects (workcenter + mbom + routing + operation)"
workcenter_code="WC-${ts}"
workcenter_json="${OUT_DIR}/workcenter_create.json"
request_json POST "/api/v1/workcenters" "$workcenter_json" \
  "{\"code\":\"${workcenter_code}\",\"name\":\"RelOrch WorkCenter ${ts}\",\"plant_code\":\"PLANT-1\",\"department_code\":\"LINE-1\",\"is_active\":true}"
workcenter_id="$(json_id "$workcenter_json")"
[[ -n "$workcenter_id" ]] || fail "failed to parse workcenter id"

mbom_json="${OUT_DIR}/mbom_create.json"
request_json POST "/api/v1/mboms/from-ebom" "$mbom_json" \
  "{\"source_item_id\":\"${parent_id}\",\"name\":\"RelOrch MBOM ${ts}\",\"version\":\"1.0\",\"plant_code\":\"PLANT-1\"}"
mbom_id="$(json_id "$mbom_json")"
[[ -n "$mbom_id" ]] || fail "failed to parse mbom id"

routing_json="${OUT_DIR}/routing_create.json"
request_json POST "/api/v1/routings" "$routing_json" \
  "{\"name\":\"RelOrch Routing ${ts}\",\"mbom_id\":\"${mbom_id}\",\"item_id\":\"${parent_id}\",\"version\":\"1.0\",\"is_primary\":true,\"plant_code\":\"PLANT-1\",\"line_code\":\"LINE-1\"}"
routing_id="$(json_id "$routing_json")"
[[ -n "$routing_id" ]] || fail "failed to parse routing id"

request_json POST "/api/v1/routings/${routing_id}/operations" "${OUT_DIR}/routing_operation_create.json" \
  "{\"operation_number\":\"10\",\"name\":\"RelOrch Operation\",\"operation_type\":\"fabrication\",\"workcenter_id\":\"${workcenter_id}\",\"setup_time\":5,\"run_time\":1,\"sequence\":10}"
item_generation="1"

log "Create incomplete e-sign manifest (approved required)"
esign_manifest_json="${OUT_DIR}/esign_manifest_create.json"
request_json POST "/api/v1/esign/manifests" "$esign_manifest_json" \
  "{\"item_id\":\"${parent_id}\",\"generation\":${item_generation},\"required_signatures\":[{\"meaning\":\"approved\",\"role\":\"admin\",\"required\":true}]}"
manifest_complete="$(json_get "$esign_manifest_json" is_complete)"
assert_eq "manifest.is_complete" "$manifest_complete" "False"

log "Release orchestration: plan (via helper script; login path)"
plan_json="${OUT_DIR}/release_orchestration_plan.json"
"${REPO_ROOT}/scripts/release_orchestration.sh" plan "$parent_id" \
  --base "$BASE_URL" --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --out "$plan_json" >/dev/null

"$PY_BIN" - "$plan_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
steps = data.get("steps") or []
requires_esign = [s for s in steps if (s or {}).get("action") == "requires_esign"]
print(f"plan_steps_total={len(steps)} requires_esign={len(requires_esign)}")
if not requires_esign:
  raise SystemExit("expected at least 1 step with action=requires_esign")
PY

log "Release orchestration: execute (expects baseline blocked + rollback) via helper script"
execute_blocked_json="${OUT_DIR}/release_orchestration_execute_blocked.json"
exec_args=(
  execute "$parent_id"
  --base "$BASE_URL" --tenant "$TENANT_ID" --org "$ORG_ID"
  --username "$USERNAME" --password "$PASSWORD"
  --include-baselines
  --rollback-on-failure
  --out "$execute_blocked_json"
)
if [[ "$baseline_force" == "true" ]]; then
  exec_args+=(--baseline-force)
fi
"${REPO_ROOT}/scripts/release_orchestration.sh" "${exec_args[@]}" >/dev/null

"$PY_BIN" - "$execute_blocked_json" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
results = data.get("results") or []
def has(kind, status):
  return any((r or {}).get("kind") == kind and (r or {}).get("status") == status for r in results)
required = [
  ("routing_release", "executed"),
  ("mbom_release", "executed"),
  ("baseline_release", "blocked_esign_incomplete"),
  ("mbom_reopen", "rolled_back"),
  ("routing_reopen", "rolled_back"),
]
missing = [(k,s) for (k,s) in required if not has(k,s)]
print(f"execute_results_total={len(results)} missing_required={len(missing)}")
if missing:
  raise SystemExit("missing expected results: " + ", ".join([f"{k}:{s}" for k,s in missing]))
PY

log "Complete manifest by signing meaning=approved"
esign_sign_json="${OUT_DIR}/esign_sign.json"
request_json POST "/api/v1/esign/sign" "$esign_sign_json" "{\"item_id\":\"${parent_id}\",\"meaning\":\"approved\"}"
signature_id="$(json_get "$esign_sign_json" id)"
[[ -n "$signature_id" ]] || fail "failed to parse signature id"

request_json POST "/api/v1/esign/verify/${signature_id}" "${OUT_DIR}/esign_verify.json"

esign_status_json="${OUT_DIR}/esign_manifest_status.json"
request_json GET "/api/v1/esign/manifests/${parent_id}" "$esign_status_json"
manifest_complete="$(json_get "$esign_status_json" is_complete)"
assert_eq "manifest.is_complete_after_sign" "$manifest_complete" "True"

log "Release orchestration: execute again (expects all released) via helper script"
execute_ok_json="${OUT_DIR}/release_orchestration_execute_ok.json"
exec2_args=(
  execute "$parent_id"
  --base "$BASE_URL" --tenant "$TENANT_ID" --org "$ORG_ID"
  --username "$USERNAME" --password "$PASSWORD"
  --include-baselines
  --out "$execute_ok_json"
)
if [[ "$baseline_force" == "true" ]]; then
  exec2_args+=(--baseline-force)
fi
"${REPO_ROOT}/scripts/release_orchestration.sh" "${exec2_args[@]}" >/dev/null

baseline_after="${OUT_DIR}/baseline_after.json"
routing_after="${OUT_DIR}/routing_after.json"
mbom_list_after="${OUT_DIR}/mboms_after.json"
request_json GET "/api/v1/baselines/${baseline_id}" "$baseline_after"
request_json GET "/api/v1/routings/${routing_id}" "$routing_after"
request_json GET "/api/v1/mboms?source_item_id=${parent_id}&include_structure=false" "$mbom_list_after"

assert_eq "baseline.state" "$(json_get "$baseline_after" state)" "released"
assert_eq "routing.state" "$(json_get "$routing_after" state)" "released"
"$PY_BIN" - "$mbom_list_after" "$mbom_id" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  items = json.load(f)
target = sys.argv[2]
found = None
if isinstance(items, list):
  for it in items:
    if isinstance(it, dict) and it.get("id") == target:
      found = it
      break
if not found:
  raise SystemExit(f"mbom not found in list response: {target}")
state = (found.get("state") or "").strip()
if state != "released":
  raise SystemExit(f"mbom.state expected released, got {state!r}")
print(f"mbom.state={state}")
PY

log "ALL CHECKS PASSED out=${OUT_DIR}"
