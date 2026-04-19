#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  BASE_URL=http://localhost:8000 TOKEN=<jwt> scripts/run_p2_observation_regression.sh
  BASE_URL=http://localhost:8000 USERNAME=<user> PASSWORD=<password> scripts/run_p2_observation_regression.sh
  scripts/run_p2_observation_regression.sh --env-file "$HOME/.config/yuantus/p2-shared-dev.env"

Options:
  --env-file <path>      Load unset wrapper env vars from a local KEY=VALUE file
                         File values act as defaults; already-exported env wins
  --archive              Force tar.gz archive creation after the run
  -h, --help             Show this help

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
  ENV_FILE              Optional default env file, same behavior as --env-file
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
  ARCHIVE_RESULT        Optional. Set to 1 to tar.gz the result directory
  ARCHIVE_PATH          Optional. Archive output path
                        default: <OUTPUT_DIR>.tar.gz
  COMPANY_ID            Optional filter forwarded to verify_p2_dev_observation_startup.sh
  ECO_TYPE              Optional filter forwarded to verify_p2_dev_observation_startup.sh
  ECO_STATE             Optional filter forwarded to verify_p2_dev_observation_startup.sh
  DEADLINE_FROM         Optional filter forwarded to verify_p2_dev_observation_startup.sh
  DEADLINE_TO           Optional filter forwarded to verify_p2_dev_observation_startup.sh
  RUN_WRITE_SMOKE       Optional. Set to 1 to exercise write endpoints
  AUTO_ASSIGN_ECO_ID    Required when RUN_WRITE_SMOKE=1

Behavior:
  0. If ENV_FILE/--env-file is provided, load missing wrapper env defaults from it
  0. If TOKEN is absent, logs in via /api/v1/auth/login using USERNAME/PASSWORD
  1. Runs verify_p2_dev_observation_startup.sh
  2. Renders OBSERVATION_RESULT.md
  3. If BASELINE_DIR is set, renders OBSERVATION_DIFF.md
  4. If EVAL_MODE is set, renders OBSERVATION_EVAL.md
  5. If ARCHIVE_RESULT=1 or --archive is passed, writes <OUTPUT_DIR>.tar.gz
EOF
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: $name" >&2
    usage >&2
    exit 1
  fi
}

load_env_file() {
  local env_file="$1"
  local key=""
  local value=""
  local parser="python3"

  if [[ ! -f "${env_file}" ]]; then
    echo "Missing env file: ${env_file}" >&2
    exit 1
  fi

  while IFS='=' read -r key value; do
    [[ -n "${key}" ]] || continue
    if [[ -z "${!key+x}" ]]; then
      printf -v "${key}" '%s' "${value}"
      export "${key}"
    fi
  done < <(
    "${parser}" - "${env_file}" <<'PY'
import re
import shlex
import sys
from pathlib import Path

allowed = {
    "ARCHIVE_PATH",
    "ARCHIVE_RESULT",
    "AUTO_ASSIGN_ECO_ID",
    "BASELINE_DIR",
    "BASELINE_LABEL",
    "BASE_URL",
    "COMPANY_ID",
    "CURRENT_LABEL",
    "DEADLINE_FROM",
    "DEADLINE_TO",
    "ECO_STATE",
    "ECO_TYPE",
    "ENVIRONMENT",
    "EVAL_MODE",
    "EVAL_OUTPUT",
    "EXPECT_DELTAS",
    "OPERATOR",
    "ORG_ID",
    "OUTPUT_DIR",
    "PASSWORD",
    "PY",
    "RUN_WRITE_SMOKE",
    "TENANT_ID",
    "TOKEN",
    "USERNAME",
}

path = Path(sys.argv[1])
for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        continue
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        raise SystemExit(f"{path}:{lineno}: expected KEY=VALUE")
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
        raise SystemExit(f"{path}:{lineno}: invalid env key '{key}'")
    if key not in allowed:
        raise SystemExit(f"{path}:{lineno}: unsupported env key '{key}'")
    if value and value[0] in "\"'":
        parsed = shlex.split(value, posix=True)
        if len(parsed) != 1:
            raise SystemExit(f"{path}:{lineno}: quoted value must resolve to one token")
        value = parsed[0]
    print(f"{key}={value}")
PY
  )
}

env_file_arg=""
archive_flag="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --env-file)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "Missing value for --env-file" >&2
        usage >&2
        exit 1
      fi
      env_file_arg="$2"
      shift 2
      ;;
    --archive)
      archive_flag="1"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

env_file_path="${env_file_arg:-${ENV_FILE:-}}"
if [[ -n "${env_file_path}" ]]; then
  load_env_file "${env_file_path}"
fi

require_env BASE_URL

timestamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${OUTPUT_DIR:-./tmp/p2-observation-rerun-${timestamp}}"
operator="${OPERATOR:-${USER:-unknown}}"
environment_name="${ENVIRONMENT:-regression}"
baseline_label="${BASELINE_LABEL:-baseline}"
current_label="${CURRENT_LABEL:-current}"
eval_output="${EVAL_OUTPUT:-${output_dir}/OBSERVATION_EVAL.md}"
archive_result="${ARCHIVE_RESULT:-0}"
archive_path="${ARCHIVE_PATH:-${output_dir%/}.tar.gz}"
PY="${PY:-python3}"

if [[ "${archive_flag}" == "1" ]]; then
  archive_result="1"
fi

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
if [[ -n "${env_file_path}" ]]; then
  echo "ENV_FILE=${env_file_path}"
fi
if [[ -n "${BASELINE_DIR:-}" ]]; then
  echo "BASELINE_DIR=${BASELINE_DIR}"
fi
if [[ "${archive_result}" == "1" ]]; then
  echo "ARCHIVE_PATH=${archive_path}"
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

if [[ "${archive_result}" == "1" ]]; then
  mkdir -p "$(dirname "${archive_path}")"
  tar -czf "${archive_path}" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
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
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${archive_path}"
fi
