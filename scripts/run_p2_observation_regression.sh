#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  BASE_URL=http://localhost:8000 TOKEN=<jwt> scripts/run_p2_observation_regression.sh
  BASE_URL=http://localhost:8000 USERNAME=<user> PASSWORD=<password> scripts/run_p2_observation_regression.sh

Required env:
  BASE_URL              API base URL
  Authentication        Either:
                        - TOKEN=<jwt>
                        - USERNAME=<user> PASSWORD=<password>

Optional env:
  TENANT_ID             x-tenant-id header value
  ORG_ID                x-org-id header value
  USERNAME              Login username when TOKEN is not provided
                        default: admin
  PASSWORD              Login password when TOKEN is not provided
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
  EVAL_MODE             Optional. current-only | readonly | state-change
  EXPECT_DELTAS         Optional. Comma-separated metric=delta pairs for state-change
                        example: overdue_count=1,escalated_count=1
  EVAL_OUTPUT           Optional. Output path for OBSERVATION_EVAL.md
                        default: <OUTPUT_DIR>/OBSERVATION_EVAL.md

Behavior:
  0. If TOKEN is absent, logs in via /api/v1/auth/login using USERNAME/PASSWORD
  1. Runs verify_p2_dev_observation_startup.sh
  2. Renders OBSERVATION_RESULT.md
  3. If BASELINE_DIR is set, renders OBSERVATION_DIFF.md
  4. If EVAL_MODE is set, renders OBSERVATION_EVAL.md
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

timestamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${OUTPUT_DIR:-./tmp/p2-observation-rerun-${timestamp}}"
operator="${OPERATOR:-${USER:-unknown}}"
environment_name="${ENVIRONMENT:-regression}"
baseline_label="${BASELINE_LABEL:-baseline}"
current_label="${CURRENT_LABEL:-current}"
eval_output="${EVAL_OUTPUT:-${output_dir}/OBSERVATION_EVAL.md}"
PY="${PY:-python3}"

ensure_token() {
  if [[ -n "${TOKEN:-}" ]]; then
    return 0
  fi

  if [[ -z "${PASSWORD:-}" ]]; then
    echo "Missing authentication env: provide TOKEN or PASSWORD (with optional USERNAME)" >&2
    usage >&2
    exit 1
  fi

  local login_json
  local login_body
  local username
  local code
  username="${USERNAME:-admin}"
  login_json="$(mktemp)"
  trap 'rm -f "$login_json" >/dev/null 2>&1 || true' RETURN

  login_body="$(
    TENANT_ID_VALUE="${TENANT_ID:-}" \
    ORG_ID_VALUE="${ORG_ID:-}" \
    USERNAME_VALUE="${username}" \
    PASSWORD_VALUE="${PASSWORD}" \
    "$PY" - <<'PY'
import json
import os
import sys

payload = {
    "tenant_id": os.environ["TENANT_ID_VALUE"],
    "org_id": os.environ["ORG_ID_VALUE"],
    "username": os.environ["USERNAME_VALUE"],
    "password": os.environ["PASSWORD_VALUE"],
}
json.dump(payload, sys.stdout, ensure_ascii=True, separators=(",", ":"))
PY
  )"

  code="$(
    curl -sS -o "$login_json" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/auth/login" \
      -H 'content-type: application/json' \
      --data-binary "${login_body}"
  )"
  if [[ "${code}" != "200" ]]; then
    echo "ERROR: observation login failed -> HTTP ${code}" >&2
    cat "$login_json" >&2 || true
    exit 1
  fi

  TOKEN="$(
    LOGIN_JSON_PATH="${login_json}" \
    "$PY" - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["LOGIN_JSON_PATH"]).read_text(encoding="utf-8"))
access_token = payload.get("access_token")
if not isinstance(access_token, str) or not access_token:
    raise SystemExit("missing access_token in login response")
print(access_token)
PY
  )"
  if [[ -z "${TOKEN}" ]]; then
    echo "ERROR: failed to parse access_token from login response" >&2
    exit 1
  fi
}

ensure_token

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

if [[ -n "${EVAL_MODE:-}" ]]; then
  eval_cmd=(
    python3 scripts/evaluate_p2_observation_results.py
    "${output_dir}"
    --mode "${EVAL_MODE}"
    --output "${eval_output}"
  )
  if [[ -n "${BASELINE_DIR:-}" ]]; then
    eval_cmd+=(--baseline-dir "${BASELINE_DIR}")
  fi
  if [[ -n "${EXPECT_DELTAS:-}" ]]; then
    old_ifs="$IFS"
    IFS=','
    read -r -a expect_delta_pairs <<< "${EXPECT_DELTAS}"
    IFS="$old_ifs"
    for pair in "${expect_delta_pairs[@]}"; do
      [[ -n "${pair}" ]] || continue
      eval_cmd+=(--expect-delta "${pair}")
    done
  fi
  "${eval_cmd[@]}"
fi

echo
echo "Done:"
echo "  ${output_dir}/OBSERVATION_RESULT.md"
if [[ -n "${BASELINE_DIR:-}" ]]; then
  echo "  ${output_dir}/OBSERVATION_DIFF.md"
fi
if [[ -n "${EVAL_MODE:-}" ]]; then
  echo "  ${eval_output}"
fi
