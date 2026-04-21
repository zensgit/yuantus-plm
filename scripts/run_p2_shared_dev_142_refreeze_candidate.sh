#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_refreeze_candidate.sh [options]

Options:
  --env-file <path>    Observation env file
                       default: $HOME/.config/yuantus/p2-shared-dev.env
  --output-dir <path>  Result directory
                       default: ./tmp/p2-shared-dev-142-refreeze-candidate-<timestamp>
  --skip-precheck      Skip precheck before the nested readonly rerun
  --no-archive         Do not write <OUTPUT_DIR>.tar.gz
  -h, --help           Show this help

Behavior:
  - validates the shared-dev observation env
  - runs the fixed shared-dev 142 readonly rerun into <OUTPUT_DIR>/current
  - delegates the source capture to scripts/run_p2_shared_dev_142_readonly_rerun.sh
  - continues even if readonly rerun returns non-zero
  - renders a stable candidate preview by excluding future-deadline pending approvals
  - writes:
    - <OUTPUT_DIR>/STABLE_READONLY_CANDIDATE.md
    - <OUTPUT_DIR>/stable_readonly_candidate.json
    - <OUTPUT_DIR>/candidate/*
EOF
}

default_env_file="${HOME}/.config/yuantus/p2-shared-dev.env"
timestamp="$(date +%Y%m%d-%H%M%S)"

env_file="${default_env_file}"
output_dir="./tmp/p2-shared-dev-142-refreeze-candidate-${timestamp}"
run_precheck="1"
archive_result="1"

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "${value}" ]]; then
    echo "Missing value for ${flag}" >&2
    usage >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      require_value "$1" "${2:-}"
      env_file="$2"
      shift 2
      ;;
    --output-dir)
      require_value "$1" "${2:-}"
      output_dir="$2"
      shift 2
      ;;
    --skip-precheck)
      run_precheck="0"
      shift
      ;;
    --no-archive)
      archive_result="0"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

output_dir="${output_dir%/}"
current_dir="${output_dir}/current"
candidate_dir="${output_dir}/candidate"
candidate_md="${output_dir}/STABLE_READONLY_CANDIDATE.md"
candidate_json="${output_dir}/stable_readonly_candidate.json"

echo "== Shared-dev 142 readonly refreeze candidate =="
echo "ENV_FILE=${env_file}"
echo "OUTPUT_DIR=${output_dir}"
echo "RUN_PRECHECK=${run_precheck}"
echo "ARCHIVE_RESULT=${archive_result}"
echo

bash scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "${env_file}"

readonly_args=(
  --env-file "${env_file}"
  --output-dir "${current_dir}"
  --no-archive
)
if [[ "${run_precheck}" == "0" ]]; then
  readonly_args+=(--skip-precheck)
fi

readonly_status=0
if ! bash scripts/run_p2_shared_dev_142_readonly_rerun.sh "${readonly_args[@]}"; then
  readonly_status=$?
  echo "Readonly rerun exited with status ${readonly_status}; continuing to render stable candidate." >&2
fi

python3 scripts/render_p2_shared_dev_142_refreeze_candidate.py \
  "${current_dir}" \
  --output-dir "${candidate_dir}" \
  --output-md "${candidate_md}" \
  --output-json "${candidate_json}"

candidate_ready="$(
  python3 - "${candidate_json}" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(1 if payload.get("candidate_ready") else 0)
PY
)"
candidate_kind="$(
  python3 - "${candidate_json}" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("decision", {}).get("kind", "unknown"))
PY
)"
excluded_pending_count="$(
  python3 - "${candidate_json}" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(len(payload.get("excluded_pending_items", [])))
PY
)"

if [[ "${archive_result}" == "1" ]]; then
  tar -czf "${output_dir}.tar.gz" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
fi

echo
echo "READONLY_EXIT_STATUS=${readonly_status}"
echo "CANDIDATE_READY=${candidate_ready}"
echo "CANDIDATE_DECISION_KIND=${candidate_kind}"
echo "EXCLUDED_PENDING_COUNT=${excluded_pending_count}"
echo "Done:"
echo "  ${current_dir}/OBSERVATION_RESULT.md"
echo "  ${candidate_md}"
echo "  ${candidate_json}"
echo "  ${candidate_dir}/OBSERVATION_RESULT.md"
echo "  ${candidate_dir}/OBSERVATION_EVAL.md"
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${output_dir}.tar.gz"
fi

if [[ "${candidate_ready}" != "1" ]]; then
  exit 1
fi
