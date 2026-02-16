#!/usr/bin/env bash
set -euo pipefail

# Self-contained perf smoke for release orchestration endpoints.
#
# Coverage:
# - GET /api/v1/release-orchestration/items/{item_id}/plan
# - POST /api/v1/release-orchestration/items/{item_id}/execute (dry_run=true)
#
# The script starts a temporary local server backed by an isolated SQLite DB,
# executes several timing samples, and asserts p95 latency thresholds.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/verify-release-orchestration-perf/${timestamp}"
OUT_DIR="${OUT_DIR:-$OUT_DIR_DEFAULT}"
mkdir -p "$OUT_DIR"

SAMPLES="${PERF_RELEASE_ORCH_SAMPLES:-5}"
PLAN_MAX_MS="${PERF_RELEASE_ORCH_PLAN_MAX_MS:-1800}"
EXEC_DRY_RUN_MAX_MS="${PERF_RELEASE_ORCH_EXECUTE_DRY_RUN_MAX_MS:-2200}"

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
  PORT="$($PY_BIN - <<'PY'
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

DB_PATH="${DB_PATH:-/tmp/yuantus_verify_release_orch_perf_${timestamp}.db}"
db_path_norm="${DB_PATH#/}"

export PYTHONPATH="${PYTHONPATH:-src}"
export YUANTUS_TENANCY_MODE="single"
export YUANTUS_SCHEMA_MODE="create_all"
export YUANTUS_DATABASE_URL="sqlite:////${db_path_norm}"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:////${db_path_norm}"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

plan_ms_file="${OUT_DIR}/plan_ms.txt"
exec_ms_file="${OUT_DIR}/execute_dry_run_ms.txt"
: > "$plan_ms_file"
: > "$exec_ms_file"

log "Seed identity/meta (db=${DB_PATH})"
"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin --superuser >/dev/null
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

TOKEN="$($PY_BIN - "$login_json" <<'PY'
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

timed_request_json() {
  local method="$1"
  local path="$2"
  local out_path="$3"
  local time_out_path="$4"
  local data="${5:-}"

  local url="${BASE_URL}${path}"
  local meta
  if [[ -n "$data" ]]; then
    meta="$(curl -sS -o "$out_path" -w "%{http_code} %{time_total}" -X "$method" "$url" "${auth_header[@]}" "${json_header[@]}" -d "$data")"
  else
    meta="$(curl -sS -o "$out_path" -w "%{http_code} %{time_total}" -X "$method" "$url" "${auth_header[@]}")"
  fi

  local http_code="${meta%% *}"
  local time_total="${meta#* }"

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    cat "$out_path" >&2 || true
    fail "${method} ${path} -> HTTP ${http_code}"
  fi

  "$PY_BIN" - "$time_total" "$time_out_path" <<'PY'
import sys
seconds = float(sys.argv[1])
out_path = sys.argv[2]
ms = seconds * 1000.0
with open(out_path, "a", encoding="utf-8") as f:
  f.write(f"{ms:.3f}\n")
print(f"{ms:.3f}")
PY
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

assert_p95_under() {
  local label="$1"
  local ms_file="$2"
  local max_ms="$3"
  local out_json="$4"

  "$PY_BIN" - "$label" "$ms_file" "$max_ms" "$out_json" <<'PY'
import json
import math
import statistics
import sys

label = sys.argv[1]
path = sys.argv[2]
threshold = float(sys.argv[3])
out_json = sys.argv[4]
values = []
with open(path, "r", encoding="utf-8") as f:
    for raw in f:
        s = raw.strip()
        if s:
            values.append(float(s))
if not values:
    raise SystemExit(f"{label}: no samples")

sorted_vals = sorted(values)
idx = max(0, min(len(sorted_vals) - 1, int(math.ceil(0.95 * len(sorted_vals))) - 1))
p95 = sorted_vals[idx]
p50 = statistics.median(values)

payload = {
    "label": label,
    "samples": len(values),
    "threshold_ms": threshold,
    "p50_ms": round(p50, 3),
    "p95_ms": round(p95, 3),
    "values_ms": values,
}
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

print(f"{label}: samples={len(values)} p50={p50:.3f}ms p95={p95:.3f}ms threshold={threshold:.3f}ms")
if p95 > threshold:
    raise SystemExit(f"{label}: p95 {p95:.3f}ms exceeds threshold {threshold:.3f}ms")
PY
}

ts="$(date +%s)"
parent_number="RELORCH-PERF-P-${ts}"
child_number="RELORCH-PERF-C-${ts}"

log "Create items + baseline + manufacturing fixtures"
parent_json="${OUT_DIR}/part_parent.json"
request_json POST "/api/v1/aml/apply" "$parent_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${parent_number}\",\"name\":\"RelOrch Perf Parent ${ts}\"}}"
parent_id="$(json_id "$parent_json")"
[[ -n "$parent_id" ]] || fail "failed to parse parent item id"

child_json="${OUT_DIR}/part_child.json"
request_json POST "/api/v1/aml/apply" "$child_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${child_number}\",\"name\":\"RelOrch Perf Child ${ts}\"}}"
child_id="$(json_id "$child_json")"
[[ -n "$child_id" ]] || fail "failed to parse child item id"

request_json POST "/api/v1/bom/${parent_id}/children" "${OUT_DIR}/bom_add_child.json" \
  "{\"child_id\":\"${child_id}\",\"quantity\":1,\"uom\":\"EA\"}"

baseline_json="${OUT_DIR}/baseline_create.json"
request_json POST "/api/v1/baselines" "$baseline_json" \
  "{\"name\":\"RelOrch Perf Baseline ${ts}\",\"root_item_id\":\"${parent_id}\",\"auto_populate\":true}"

mbom_json="${OUT_DIR}/mbom_create.json"
request_json POST "/api/v1/mboms/from-ebom" "$mbom_json" \
  "{\"source_item_id\":\"${parent_id}\",\"name\":\"RelOrch Perf MBOM ${ts}\",\"version\":\"1.0\",\"plant_code\":\"PLANT-1\"}"
mbom_id="$(json_id "$mbom_json")"
[[ -n "$mbom_id" ]] || fail "failed to parse mbom id"

workcenter_json="${OUT_DIR}/workcenter_create.json"
request_json POST "/api/v1/workcenters" "$workcenter_json" \
  "{\"code\":\"WC-PERF-${ts}\",\"name\":\"RelOrch Perf WC ${ts}\",\"plant_code\":\"PLANT-1\",\"department_code\":\"LINE-1\",\"is_active\":true}"
workcenter_id="$(json_id "$workcenter_json")"
[[ -n "$workcenter_id" ]] || fail "failed to parse workcenter id"

routing_json="${OUT_DIR}/routing_create.json"
request_json POST "/api/v1/routings" "$routing_json" \
  "{\"name\":\"RelOrch Perf Routing ${ts}\",\"mbom_id\":\"${mbom_id}\",\"item_id\":\"${parent_id}\",\"version\":\"1.0\",\"is_primary\":true,\"plant_code\":\"PLANT-1\",\"line_code\":\"LINE-1\"}"
routing_id="$(json_id "$routing_json")"
[[ -n "$routing_id" ]] || fail "failed to parse routing id"

request_json POST "/api/v1/routings/${routing_id}/operations" "${OUT_DIR}/routing_operation_create.json" \
  "{\"operation_number\":\"10\",\"name\":\"RelOrch Perf Op\",\"operation_type\":\"fabrication\",\"workcenter_id\":\"${workcenter_id}\",\"setup_time\":5,\"run_time\":1,\"sequence\":10}"

log "Run timed samples (count=${SAMPLES})"
for i in $(seq 1 "$SAMPLES"); do
  plan_out="${OUT_DIR}/plan_${i}.json"
  plan_ms="$(timed_request_json GET "/api/v1/release-orchestration/items/${parent_id}/plan?ruleset_id=default" "$plan_out" "$plan_ms_file")"

  exec_out="${OUT_DIR}/execute_${i}.json"
  exec_ms="$(timed_request_json POST "/api/v1/release-orchestration/items/${parent_id}/execute" "$exec_out" "$exec_ms_file" '{"ruleset_id":"default","include_routings":true,"include_mboms":true,"include_baselines":true,"dry_run":true,"baseline_force":true}')"

  "$PY_BIN" - "$plan_out" "$exec_out" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    plan = json.load(f)
with open(sys.argv[2], "r", encoding="utf-8") as f:
    execute = json.load(f)

if not plan.get("item_id"):
    raise SystemExit("plan missing item_id")
if not isinstance(plan.get("steps") or [], list):
    raise SystemExit("plan.steps must be a list")
if not isinstance(execute.get("results") or [], list):
    raise SystemExit("execute.results must be a list")
PY

  log "sample#${i}: plan=${plan_ms}ms execute_dry_run=${exec_ms}ms"
done

metrics_plan_json="${OUT_DIR}/metrics_plan.json"
metrics_exec_json="${OUT_DIR}/metrics_execute_dry_run.json"
assert_p95_under "release_orchestration.plan" "$plan_ms_file" "$PLAN_MAX_MS" "$metrics_plan_json"
assert_p95_under "release_orchestration.execute_dry_run" "$exec_ms_file" "$EXEC_DRY_RUN_MAX_MS" "$metrics_exec_json"

"$PY_BIN" - "$metrics_plan_json" "$metrics_exec_json" "${OUT_DIR}/metrics_summary.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    plan = json.load(f)
with open(sys.argv[2], "r", encoding="utf-8") as f:
    execute = json.load(f)

summary = {
    "release_orchestration": {
        "plan": plan,
        "execute_dry_run": execute,
    }
}
with open(sys.argv[3], "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print("metrics_summary: OK")
PY

log "ALL CHECKS PASSED out=${OUT_DIR}"
