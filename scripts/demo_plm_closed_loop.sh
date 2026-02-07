#!/usr/bin/env bash
# Demo: PLM closed-loop scenario (API-only), producing an evidence bundle.
#
# Flow:
#   EBOM -> Baseline -> MBOM -> Routing -> Diagnostics -> Release
#   -> Release Readiness -> Impact -> Item Cockpit -> Export bundles
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
run_id="${DEMO_RUN_ID:-DEMO_PLM_CLOSED_LOOP_${timestamp}}"

OUT_DIR_DEFAULT="${REPO_ROOT}/tmp/demo-plm/${timestamp}"
OUT_DIR="${DEMO_OUT_DIR:-$OUT_DIR_DEFAULT}"

REPORT_DEFAULT="${REPO_ROOT}/docs/DAILY_REPORTS/DEMO_PLM_CLOSED_LOOP_${timestamp}.md"
REPORT_PATH="${DEMO_REPORT_PATH:-$REPORT_DEFAULT}"

mkdir -p "$OUT_DIR"
mkdir -p "$(dirname "$REPORT_PATH")"

PORT="${DEMO_PORT:-0}"
if [[ "$PORT" == "0" ]]; then
  PORT="$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"
fi

BASE_URL="${DEMO_BASE_URL:-http://127.0.0.1:${PORT}}"

DB_PATH="${DEMO_DB_PATH:-/tmp/yuantus_demo_plm_${timestamp}.db}"

export PYTHONPATH="${PYTHONPATH:-src}"
export YUANTUS_TENANCY_MODE="${YUANTUS_TENANCY_MODE:-single}"
export YUANTUS_DATABASE_URL="${YUANTUS_DATABASE_URL:-sqlite:////${DB_PATH}}"
export YUANTUS_IDENTITY_DATABASE_URL="${YUANTUS_IDENTITY_DATABASE_URL:-sqlite:////${DB_PATH}}"

rm -f "${DB_PATH}" "${DB_PATH}-shm" "${DB_PATH}-wal" 2>/dev/null || true

YUANTUS_BIN="${YUANTUS_BIN:-${REPO_ROOT}/.venv/bin/yuantus}"
UVICORN_BIN="${UVICORN_BIN:-${REPO_ROOT}/.venv/bin/uvicorn}"

if [[ ! -x "$YUANTUS_BIN" ]]; then
  echo "ERROR: yuantus CLI not found at $YUANTUS_BIN" >&2
  exit 2
fi
if [[ ! -x "$UVICORN_BIN" ]]; then
  echo "ERROR: uvicorn not found at $UVICORN_BIN" >&2
  exit 2
fi

TENANT_ID="${TENANT_ID:-tenant-1}"
ORG_ID="${ORG_ID:-org-1}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin}"

"$YUANTUS_BIN" seed-identity \
  --tenant "$TENANT_ID" --org "$ORG_ID" \
  --username "$USERNAME" --password "$PASSWORD" \
  --user-id 1 --roles admin >/dev/null

"$YUANTUS_BIN" seed-meta >/dev/null

server_log="${OUT_DIR}/server.log"
"$UVICORN_BIN" yuantus.api.app:app --host 127.0.0.1 --port "$PORT" >"$server_log" 2>&1 &
server_pid="$!"

cleanup() {
  kill "$server_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for i in {1..60}; do
  if curl -sS "${BASE_URL}/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -sS "${BASE_URL}/api/v1/health" >"${OUT_DIR}/health.json"

login_json="${OUT_DIR}/login.json"
curl -sS -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "content-type: application/json" \
  -d "{\"tenant_id\":\"${TENANT_ID}\",\"org_id\":\"${ORG_ID}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
  >"$login_json"

TOKEN="$(python3 - <<PY
import json
with open("$login_json", "r", encoding="utf-8") as f:
  print(json.load(f)["access_token"])
PY
)"

auth_header=(-H "Authorization: Bearer ${TOKEN}" -H "x-tenant-id: ${TENANT_ID}" -H "x-org-id: ${ORG_ID}")
json_header=(-H "content-type: application/json")

request_json() {
  local method="$1"
  local path="$2"
  local out_path="$3"
  local data="${4:-}"

  local url="${BASE_URL}${path}"
  local code
  if [[ -n "$data" ]]; then
    code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}" "${json_header[@]}" -d "$data")"
  else
    code="$(curl -sS -o "$out_path" -w "%{http_code}" -X "$method" "$url" "${auth_header[@]}")"
  fi

  if [[ "$code" != "200" && "$code" != "201" ]]; then
    echo "ERROR: ${method} ${path} -> HTTP ${code} (body: ${out_path})" >&2
    return 1
  fi
}

json_id() {
  python3 - "$1" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
  data = json.load(f)
print(data.get("id") or "")
PY
}

ts="$(date +%s)"
parent_number="DEMO-PARENT-${ts}"
child_number="DEMO-CHILD-${ts}"

parent_json="${OUT_DIR}/part_parent.json"
request_json POST "/api/v1/aml/apply" "$parent_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${parent_number}\",\"name\":\"Demo Parent ${ts}\"}}"
parent_id="$(json_id "$parent_json")"
if [[ -z "$parent_id" ]]; then
  echo "ERROR: failed to parse parent item id" >&2
  exit 1
fi

child_json="${OUT_DIR}/part_child.json"
request_json POST "/api/v1/aml/apply" "$child_json" \
  "{\"type\":\"Part\",\"action\":\"add\",\"properties\":{\"item_number\":\"${child_number}\",\"name\":\"Demo Child ${ts}\"}}"
child_id="$(json_id "$child_json")"
if [[ -z "$child_id" ]]; then
  echo "ERROR: failed to parse child item id" >&2
  exit 1
fi

bom_add_json="${OUT_DIR}/bom_add_child.json"
request_json POST "/api/v1/bom/${parent_id}/children" "$bom_add_json" \
  "{\"child_id\":\"${child_id}\",\"quantity\":1,\"uom\":\"EA\"}"

baseline_json="${OUT_DIR}/baseline_create.json"
request_json POST "/api/v1/baselines" "$baseline_json" \
  "{\"name\":\"Demo Baseline ${ts}\",\"root_item_id\":\"${parent_id}\",\"auto_populate\":true}"
baseline_id="$(json_id "$baseline_json")"
if [[ -z "$baseline_id" ]]; then
  echo "ERROR: failed to parse baseline id" >&2
  exit 1
fi

request_json GET "/api/v1/baselines/${baseline_id}/release-diagnostics?ruleset_id=default" \
  "${OUT_DIR}/baseline_release_diagnostics.json"
request_json POST "/api/v1/baselines/${baseline_id}/release?ruleset_id=default" \
  "${OUT_DIR}/baseline_release.json" "{\"force\":false}"

workcenter_code="WC-${ts}"
workcenter_json="${OUT_DIR}/workcenter_create.json"
request_json POST "/api/v1/workcenters" "$workcenter_json" \
  "{\"code\":\"${workcenter_code}\",\"name\":\"Demo WorkCenter ${ts}\",\"plant_code\":\"PLANT-1\",\"department_code\":\"LINE-1\",\"is_active\":true}"
workcenter_id="$(json_id "$workcenter_json")"
if [[ -z "$workcenter_id" ]]; then
  echo "ERROR: failed to parse workcenter id" >&2
  exit 1
fi

mbom_json="${OUT_DIR}/mbom_create.json"
request_json POST "/api/v1/mboms/from-ebom" "$mbom_json" \
  "{\"source_item_id\":\"${parent_id}\",\"name\":\"Demo MBOM ${ts}\",\"version\":\"1.0\",\"plant_code\":\"PLANT-1\"}"
mbom_id="$(json_id "$mbom_json")"
if [[ -z "$mbom_id" ]]; then
  echo "ERROR: failed to parse mbom id" >&2
  exit 1
fi

routing_json="${OUT_DIR}/routing_create.json"
request_json POST "/api/v1/routings" "$routing_json" \
  "{\"name\":\"Demo Routing ${ts}\",\"mbom_id\":\"${mbom_id}\",\"item_id\":\"${parent_id}\",\"version\":\"1.0\",\"is_primary\":true,\"plant_code\":\"PLANT-1\",\"line_code\":\"LINE-1\"}"
routing_id="$(json_id "$routing_json")"
if [[ -z "$routing_id" ]]; then
  echo "ERROR: failed to parse routing id" >&2
  exit 1
fi

op_json="${OUT_DIR}/routing_operation_create.json"
request_json POST "/api/v1/routings/${routing_id}/operations" "$op_json" \
  "{\"operation_number\":\"10\",\"name\":\"Demo Operation\",\"operation_type\":\"fabrication\",\"workcenter_id\":\"${workcenter_id}\",\"setup_time\":5,\"run_time\":1,\"sequence\":10}"

request_json GET "/api/v1/routings/${routing_id}/release-diagnostics?ruleset_id=default" \
  "${OUT_DIR}/routing_release_diagnostics.json"
request_json PUT "/api/v1/routings/${routing_id}/release?ruleset_id=default" \
  "${OUT_DIR}/routing_release.json"

request_json GET "/api/v1/mboms/${mbom_id}/release-diagnostics?ruleset_id=default" \
  "${OUT_DIR}/mbom_release_diagnostics.json"
request_json PUT "/api/v1/mboms/${mbom_id}/release?ruleset_id=default" \
  "${OUT_DIR}/mbom_release.json"

request_json GET "/api/v1/release-readiness/items/${parent_id}?ruleset_id=readiness" \
  "${OUT_DIR}/release_readiness.json"
request_json GET "/api/v1/impact/items/${parent_id}/summary" \
  "${OUT_DIR}/impact_summary.json"
request_json GET "/api/v1/items/${parent_id}/cockpit?ruleset_id=readiness" \
  "${OUT_DIR}/item_cockpit.json"

curl -sS -o "${OUT_DIR}/impact-summary-${parent_id}.zip" \
  "${BASE_URL}/api/v1/impact/items/${parent_id}/summary/export?export_format=zip" \
  "${auth_header[@]}"
curl -sS -o "${OUT_DIR}/release-readiness-${parent_id}.zip" \
  "${BASE_URL}/api/v1/release-readiness/items/${parent_id}/export?export_format=zip&ruleset_id=readiness" \
  "${auth_header[@]}"
curl -sS -o "${OUT_DIR}/item-cockpit-${parent_id}.zip" \
  "${BASE_URL}/api/v1/items/${parent_id}/cockpit/export?export_format=zip&ruleset_id=readiness" \
  "${auth_header[@]}"

cat >"$REPORT_PATH" <<EOF
# Demo PLM Closed Loop

- Run ID: \`$run_id\`
- Base URL: \`$BASE_URL\`
- Tenant/Org: \`${TENANT_ID}/${ORG_ID}\`
- Timestamp: \`${timestamp}\`

## Entities

- Parent item: \`${parent_id}\` (\`${parent_number}\`)
- Child item: \`${child_id}\` (\`${child_number}\`)
- Baseline: \`${baseline_id}\`
- WorkCenter: \`${workcenter_id}\` (\`${workcenter_code}\`)
- MBOM: \`${mbom_id}\`
- Routing: \`${routing_id}\`

## Evidence Artifacts

- Output directory: \`$OUT_DIR\`
- API payloads:
  - \`health.json\`
  - \`baseline_release_diagnostics.json\`, \`baseline_release.json\`
  - \`routing_release_diagnostics.json\`, \`routing_release.json\`
  - \`mbom_release_diagnostics.json\`, \`mbom_release.json\`
  - \`release_readiness.json\`
  - \`impact_summary.json\`
  - \`item_cockpit.json\`
- Export bundles:
  - \`impact-summary-${parent_id}.zip\`
  - \`release-readiness-${parent_id}.zip\`
  - \`item-cockpit-${parent_id}.zip\`
EOF

echo ""
echo "Report: $REPORT_PATH"
echo "Artifacts: $OUT_DIR"
echo "DEMO_REPORT_PATH=$REPORT_PATH"
