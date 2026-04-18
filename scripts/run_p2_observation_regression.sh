#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  BASE_URL=http://localhost:8000 TOKEN=<jwt> scripts/run_p2_observation_regression.sh

Required env:
  BASE_URL              API base URL
  TOKEN                 Bearer token

Optional env:
  TENANT_ID             x-tenant-id header value
  ORG_ID                x-org-id header value
  OUTPUT_DIR            Where to store the new regression run
                        default: ./tmp/p2-observation-rerun-<timestamp>
  OPERATOR              Operator name recorded in OBSERVATION_RESULT.md
                        default: $USER or "unknown"
  ENVIRONMENT           Environment label for OBSERVATION_RESULT.md
                        default: regression
  BASELINE_DIR          Existing observation result directory to compare against
  BASELINE_LABEL        Label used in OBSERVATION_DIFF.md for the baseline column
                        default: baseline
  CURRENT_LABEL         Label used in OBSERVATION_DIFF.md for the current column
                        default: current

Behavior:
  1. Runs verify_p2_dev_observation_startup.sh
  2. Renders OBSERVATION_RESULT.md
  3. If BASELINE_DIR is set, renders OBSERVATION_DIFF.md
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
output_dir="${OUTPUT_DIR:-./tmp/p2-observation-rerun-${timestamp}}"
operator="${OPERATOR:-${USER:-unknown}}"
environment_name="${ENVIRONMENT:-regression}"
baseline_label="${BASELINE_LABEL:-baseline}"
current_label="${CURRENT_LABEL:-current}"

echo "== P2 observation regression run =="
echo "BASE_URL=${BASE_URL}"
echo "OUTPUT_DIR=${output_dir}"
echo "OPERATOR=${operator}"
echo "ENVIRONMENT=${environment_name}"
if [[ -n "${BASELINE_DIR:-}" ]]; then
  echo "BASELINE_DIR=${BASELINE_DIR}"
fi
echo

BASE_URL="${BASE_URL}" \
TOKEN="${TOKEN}" \
TENANT_ID="${TENANT_ID:-}" \
ORG_ID="${ORG_ID:-}" \
OUTPUT_DIR="${output_dir}" \
bash scripts/verify_p2_dev_observation_startup.sh

python3 scripts/render_p2_observation_result.py \
  "${output_dir}" \
  --operator "${operator}" \
  --environment "${environment_name}"

if [[ -n "${BASELINE_DIR:-}" ]]; then
  python3 scripts/compare_p2_observation_results.py \
    "${BASELINE_DIR}" \
    "${output_dir}" \
    --baseline-label "${baseline_label}" \
    --current-label "${current_label}"
fi

echo
echo "Done:"
echo "  ${output_dir}/OBSERVATION_RESULT.md"
if [[ -n "${BASELINE_DIR:-}" ]]; then
  echo "  ${output_dir}/OBSERVATION_DIFF.md"
fi
