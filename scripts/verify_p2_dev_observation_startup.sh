#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  BASE_URL=http://localhost:8000 TOKEN=<jwt> scripts/verify_p2_dev_observation_startup.sh

Required env:
  BASE_URL              API base URL, e.g. http://localhost:8000
  TOKEN                 Bearer token used for authenticated requests

Optional env:
  OUTPUT_DIR            Directory to write captured artifacts
                        default: ./tmp/p2-dev-observation-<timestamp>
  COMPANY_ID            Optional summary/items/export filter
  ECO_TYPE              Optional summary/items/export filter
  ECO_STATE             Optional summary/items/export filter
  DEADLINE_FROM         Optional ISO datetime filter
  DEADLINE_TO           Optional ISO datetime filter
  RUN_WRITE_SMOKE       Set to 1 to exercise write endpoints
  AUTO_ASSIGN_ECO_ID    Required when RUN_WRITE_SMOKE=1

Notes:
  - Read endpoints are always exercised.
  - Write endpoints are opt-in because they mutate workflow state.
  - Captured payloads are written under OUTPUT_DIR for runbook/template evidence.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: $name" >&2
    usage >&2
    exit 1
  fi
}

require_env BASE_URL
require_env TOKEN

timestamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${OUTPUT_DIR:-./tmp/p2-dev-observation-${timestamp}}"
mkdir -p "${output_dir}"

auth_header="Authorization: Bearer ${TOKEN}"

build_query() {
  local first=1
  local query=""
  local add_pair=""

  add_pair() {
    local key="$1"
    local value="$2"
    if [[ -z "${value}" ]]; then
      return
    fi
    if [[ ${first} -eq 1 ]]; then
      query+="?${key}=${value}"
      first=0
    else
      query+="&${key}=${value}"
    fi
  }

  add_pair "company_id" "${COMPANY_ID:-}"
  add_pair "eco_type" "${ECO_TYPE:-}"
  add_pair "eco_state" "${ECO_STATE:-}"
  add_pair "deadline_from" "${DEADLINE_FROM:-}"
  add_pair "deadline_to" "${DEADLINE_TO:-}"

  printf '%s' "${query}"
}

query="$(build_query)"

request() {
  local method="$1"
  local path="$2"
  local outfile="$3"
  local expected_codes="$4"
  local url="${BASE_URL}${path}"
  local status

  status="$(curl -sS \
    -X "${method}" \
    -H "${auth_header}" \
    -H "Accept: application/json" \
    -o "${outfile}" \
    -w "%{http_code}" \
    "${url}")"

  case ",${expected_codes}," in
    *,"${status}",*)
      echo "[ok] ${method} ${path} -> ${status} (${outfile})"
      ;;
    *)
      echo "[fail] ${method} ${path} -> ${status}, expected one of: ${expected_codes}" >&2
      echo "Response body saved to ${outfile}" >&2
      exit 1
      ;;
  esac
}

echo "== P2 dev observation startup smoke =="
echo "BASE_URL=${BASE_URL}"
echo "OUTPUT_DIR=${output_dir}"
echo

request "GET" "/api/v1/eco/approvals/dashboard/summary${query}" "${output_dir}/summary.json" "200"
request "GET" "/api/v1/eco/approvals/dashboard/items${query}" "${output_dir}/items.json" "200"
request "GET" "/api/v1/eco/approvals/dashboard/export?fmt=json${query:+&${query#\?}}" "${output_dir}/export.json" "200"
request "GET" "/api/v1/eco/approvals/dashboard/export?fmt=csv${query:+&${query#\?}}" "${output_dir}/export.csv" "200"
request "GET" "/api/v1/eco/approvals/audit/anomalies" "${output_dir}/anomalies.json" "200"

if [[ "${RUN_WRITE_SMOKE:-0}" == "1" ]]; then
  require_env AUTO_ASSIGN_ECO_ID
  request "POST" "/api/v1/eco/${AUTO_ASSIGN_ECO_ID}/auto-assign-approvers" "${output_dir}/auto_assign.json" "200,400,403"
  request "POST" "/api/v1/eco/approvals/escalate-overdue" "${output_dir}/escalate.json" "200,403"
else
  echo "[skip] write smoke disabled (set RUN_WRITE_SMOKE=1 to enable)"
fi

cat > "${output_dir}/README.txt" <<EOF
P2 Dev Observation Startup Smoke
Timestamp: ${timestamp}
Base URL: ${BASE_URL}
Filters:
  company_id=${COMPANY_ID:-}
  eco_type=${ECO_TYPE:-}
  eco_state=${ECO_STATE:-}
  deadline_from=${DEADLINE_FROM:-}
  deadline_to=${DEADLINE_TO:-}
Write smoke enabled: ${RUN_WRITE_SMOKE:-0}

Artifacts:
  summary.json
  items.json
  export.json
  export.csv
  anomalies.json
  auto_assign.json (optional)
  escalate.json (optional)
EOF

echo
echo "Artifacts written to ${output_dir}"
echo "Next:"
echo "  1. Fill docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md section 2 / 10"
echo "  2. Fill docs/P2_OPS_OBSERVATION_TEMPLATE.md daily baseline row"
echo "  3. Attach export.csv and anomalies.json as observation evidence"
