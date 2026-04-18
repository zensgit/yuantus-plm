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
  TENANT_ID             Optional x-tenant-id header (required in db-per-tenant modes)
  ORG_ID                Optional x-org-id header (required in db-per-tenant-org mode)

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

while [[ "${BASE_URL}" == */ ]]; do
  BASE_URL="${BASE_URL%/}"
done

timestamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${OUTPUT_DIR:-./tmp/p2-dev-observation-${timestamp}}"
mkdir -p "${output_dir}"

auth_header="Authorization: Bearer ${TOKEN}"
tenant_header=()
org_header=()

if [[ -n "${TENANT_ID:-}" ]]; then
  tenant_header=(-H "x-tenant-id: ${TENANT_ID}")
fi

if [[ -n "${ORG_ID:-}" ]]; then
  org_header=(-H "x-org-id: ${ORG_ID}")
fi

urlencode() {
  local value="$1"
  local encoded=""
  local char=""
  local i=0

  for ((i = 0; i < ${#value}; i++)); do
    char="${value:i:1}"
    case "${char}" in
      [a-zA-Z0-9.~_-])
        encoded+="${char}"
        ;;
      *)
        printf -v char '%%%02X' "'${char}"
        encoded+="${char}"
        ;;
    esac
  done

  printf '%s' "${encoded}"
}

build_query() {
  local query=""
  local parts=()
  local value=""
  local i=0

  value="${COMPANY_ID:-}"
  if [[ -n "${value}" ]]; then
    parts+=("company_id=$(urlencode "${value}")")
  fi

  value="${ECO_TYPE:-}"
  if [[ -n "${value}" ]]; then
    parts+=("eco_type=$(urlencode "${value}")")
  fi

  value="${ECO_STATE:-}"
  if [[ -n "${value}" ]]; then
    parts+=("eco_state=$(urlencode "${value}")")
  fi

  value="${DEADLINE_FROM:-}"
  if [[ -n "${value}" ]]; then
    parts+=("deadline_from=$(urlencode "${value}")")
  fi

  value="${DEADLINE_TO:-}"
  if [[ -n "${value}" ]]; then
    parts+=("deadline_to=$(urlencode "${value}")")
  fi

  if [[ ${#parts[@]} -gt 0 ]]; then
    query="?${parts[0]}"
    for ((i = 1; i < ${#parts[@]}; i++)); do
      query+="&${parts[i]}"
    done
  fi

  printf '%s' "${query}"
}

query="$(build_query)"

request() {
  local method="$1"
  local path="$2"
  local outfile="$3"
  local expected_codes="$4"
  local accept_header="${5:-application/json}"
  local url="${BASE_URL}${path}"
  local status
  local curl_args=(
    -sS
    --connect-timeout 10
    --max-time 30
    -X "${method}"
    -H "${auth_header}"
    -H "Accept: ${accept_header}"
  )

  if [[ ${#tenant_header[@]} -gt 0 ]]; then
    curl_args+=("${tenant_header[@]}")
  fi

  if [[ ${#org_header[@]} -gt 0 ]]; then
    curl_args+=("${org_header[@]}")
  fi

  curl_args+=(
    -o "${outfile}"
    -w "%{http_code}"
    "${url}"
  )

  status="$(curl "${curl_args[@]}")"

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
request "GET" "/api/v1/eco/approvals/dashboard/export?fmt=csv${query:+&${query#\?}}" "${output_dir}/export.csv" "200" "text/csv"
request "GET" "/api/v1/eco/approvals/audit/anomalies" "${output_dir}/anomalies.json" "200"

if [[ "${RUN_WRITE_SMOKE:-0}" == "1" ]]; then
  auto_assign_eco_id=""
  require_env AUTO_ASSIGN_ECO_ID
  auto_assign_eco_id="$(urlencode "${AUTO_ASSIGN_ECO_ID}")"
  request "POST" "/api/v1/eco/${auto_assign_eco_id}/auto-assign-approvers" "${output_dir}/auto_assign.json" "200,400,403"
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
  tenant_id=${TENANT_ID:-}
  org_id=${ORG_ID:-}
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
echo "  1. Fill docs/P2_DEV_OBSERVATION_STARTUP_CHECKLIST.md sections 5 (基线观察) and 10 (启动确认)"
echo "  2. Fill docs/P2_OPS_OBSERVATION_TEMPLATE.md daily baseline row"
echo "  3. Attach export.csv and anomalies.json as observation evidence"
