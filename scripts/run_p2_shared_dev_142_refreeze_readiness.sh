#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_refreeze_readiness.sh [options]

Options:
  --env-file <path>         Observation env file
                            default: $HOME/.config/yuantus/p2-shared-dev.env
  --output-dir <path>       Output root
                            default: ./tmp/p2-shared-dev-142-refreeze-readiness-<timestamp>
  --skip-precheck           Skip precheck inside nested readonly rerun
  --no-archive              Do not write <OUTPUT_DIR>.tar.gz
  -h, --help                Show help

Behavior:
  - runs scripts/run_p2_shared_dev_142_readonly_rerun.sh into <OUTPUT_DIR>/current
  - always renders:
    - <OUTPUT_DIR>/REFREEZE_READINESS.md
    - <OUTPUT_DIR>/refreeze_readiness.json
  - fails if current shared-dev 142 still contains future-deadline pending approvals
EOF
}

default_env_file="${HOME}/.config/yuantus/p2-shared-dev.env"
timestamp="$(date +%Y%m%d-%H%M%S)"

env_file="${default_env_file}"
output_dir="./tmp/p2-shared-dev-142-refreeze-readiness-${timestamp}"
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
readiness_md="${output_dir}/REFREEZE_READINESS.md"
readiness_json="${output_dir}/refreeze_readiness.json"
archive_path="${output_dir}.tar.gz"

echo "== Shared-dev 142 readonly refreeze readiness =="
echo "ENV_FILE=${env_file}"
echo "OUTPUT_DIR=${output_dir}"
echo "RUN_PRECHECK=${run_precheck}"
echo "ARCHIVE_RESULT=${archive_result}"
echo

mkdir -p "${output_dir}"

readonly_cmd=(
  bash scripts/run_p2_shared_dev_142_readonly_rerun.sh
  --env-file "${env_file}"
  --output-dir "${current_dir}"
  --no-archive
)

if [[ "${run_precheck}" != "1" ]]; then
  readonly_cmd+=(--skip-precheck)
fi

readonly_status="0"
if "${readonly_cmd[@]}"; then
  readonly_status="0"
else
  readonly_status="$?"
  echo "Readonly rerun exited with status ${readonly_status}; continuing to render refreeze readiness." >&2
fi

python3 scripts/render_p2_shared_dev_142_refreeze_readiness.py \
  "${current_dir}" \
  --output-md "${readiness_md}" \
  --output-json "${readiness_json}"

if [[ "${archive_result}" == "1" ]]; then
  tar -czf "${archive_path}" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
fi

ready="$(
  python3 - <<'PY' "${readiness_json}"
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
print('1' if payload.get('ready') else '0')
PY
)"

decision_kind="$(
  python3 - <<'PY' "${readiness_json}"
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
print(payload.get('decision', {}).get('kind', 'unknown'))
PY
)"

echo
echo "Done:"
echo "  ${current_dir}/OBSERVATION_RESULT.md"
echo "  ${current_dir}/OBSERVATION_DIFF.md"
echo "  ${current_dir}/OBSERVATION_EVAL.md"
echo "  ${readiness_md}"
echo "  ${readiness_json}"
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${archive_path}"
fi
echo "READONLY_EXIT_STATUS=${readonly_status}"
echo "REFREEZE_READY=${ready}"
echo "REFREEZE_DECISION_KIND=${decision_kind}"

if [[ "${ready}" != "1" ]]; then
  exit 1
fi
