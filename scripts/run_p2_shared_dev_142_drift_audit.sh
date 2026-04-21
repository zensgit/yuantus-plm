#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_drift_audit.sh [options]

Options:
  --env-file <path>         Observation env file
                            default: $HOME/.config/yuantus/p2-shared-dev.env
  --output-dir <path>       Output root
                            default: ./tmp/p2-shared-dev-142-drift-audit-<timestamp>
  --baseline-dir <path>     Baseline directory for readonly compare/eval
                            default: ./tmp/p2-shared-dev-observation-20260421-stable
  --baseline-archive <path> Baseline archive used only when the canonical baseline dir is missing
                            default: ./tmp/p2-shared-dev-observation-20260421-stable.tar.gz
  --baseline-label <label>  Baseline label for readonly compare and drift audit
                            default: shared-dev-142-readonly-20260421
  --current-label <label>   Current label used in the drift audit
                            default: current-drift-audit
  --skip-precheck           Skip precheck and run the readonly rerun directly
  --no-restore              Do not auto-restore the canonical baseline dir from the canonical archive
  --no-archive              Do not write <OUTPUT_DIR>.tar.gz
  -h, --help                Show help

Behavior:
  - runs the current shared-dev 142 readonly rerun into <OUTPUT_DIR>/current
    via scripts/run_p2_shared_dev_142_readonly_rerun.sh
  - renders:
    - <OUTPUT_DIR>/DRIFT_AUDIT.md
    - <OUTPUT_DIR>/drift_audit.json
  - keeps the full readonly rerun evidence under:
    - <OUTPUT_DIR>/current
    - <OUTPUT_DIR>/current-precheck (unless --skip-precheck)

Boundary:
  - this is for drift investigation, not baseline promotion
  - if the deltas are expected and accepted, use the existing readonly refreeze flow afterwards
EOF
}

default_env_file="${HOME}/.config/yuantus/p2-shared-dev.env"
default_baseline_dir="./tmp/p2-shared-dev-observation-20260421-stable"
default_baseline_archive="./tmp/p2-shared-dev-observation-20260421-stable.tar.gz"
default_baseline_label="shared-dev-142-readonly-20260421"
default_current_label="current-drift-audit"
timestamp="$(date +%Y%m%d-%H%M%S)"

env_file="${default_env_file}"
output_dir="./tmp/p2-shared-dev-142-drift-audit-${timestamp}"
baseline_dir="${default_baseline_dir}"
baseline_archive="${default_baseline_archive}"
baseline_label="${default_baseline_label}"
current_label="${default_current_label}"
run_precheck="1"
allow_restore="1"
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
    --baseline-dir)
      require_value "$1" "${2:-}"
      baseline_dir="$2"
      shift 2
      ;;
    --baseline-archive)
      require_value "$1" "${2:-}"
      baseline_archive="$2"
      shift 2
      ;;
    --baseline-label)
      require_value "$1" "${2:-}"
      baseline_label="$2"
      shift 2
      ;;
    --current-label)
      require_value "$1" "${2:-}"
      current_label="$2"
      shift 2
      ;;
    --skip-precheck)
      run_precheck="0"
      shift
      ;;
    --no-restore)
      allow_restore="0"
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
drift_audit_md="${output_dir}/DRIFT_AUDIT.md"
drift_audit_json="${output_dir}/drift_audit.json"
archive_path="${output_dir}.tar.gz"

echo "== Shared-dev 142 drift audit =="
echo "ENV_FILE=${env_file}"
echo "BASELINE_DIR=${baseline_dir}"
echo "BASELINE_ARCHIVE=${baseline_archive}"
echo "BASELINE_LABEL=${baseline_label}"
echo "CURRENT_LABEL=${current_label}"
echo "OUTPUT_DIR=${output_dir}"
echo "RUN_PRECHECK=${run_precheck}"
echo "ARCHIVE_RESULT=${archive_result}"
echo

mkdir -p "${output_dir}"

readonly_cmd=(
  bash scripts/run_p2_shared_dev_142_readonly_rerun.sh
  --env-file "${env_file}"
  --output-dir "${current_dir}"
  --baseline-dir "${baseline_dir}"
  --baseline-archive "${baseline_archive}"
  --baseline-label "${baseline_label}"
  --no-archive
)

if [[ "${run_precheck}" != "1" ]]; then
  readonly_cmd+=(--skip-precheck)
fi
if [[ "${allow_restore}" != "1" ]]; then
  readonly_cmd+=(--no-restore)
fi

readonly_status="0"
if "${readonly_cmd[@]}"; then
  readonly_status="0"
else
  readonly_status="$?"
  echo "Readonly rerun exited with status ${readonly_status}; continuing to render top-level drift audit." >&2
fi

python3 scripts/render_p2_shared_dev_142_drift_audit.py \
  "${baseline_dir}" \
  "${current_dir}" \
  --baseline-label "${baseline_label}" \
  --current-label "${current_label}" \
  --output-md "${drift_audit_md}" \
  --output-json "${drift_audit_json}"

if [[ "${archive_result}" == "1" ]]; then
  mkdir -p "$(dirname "${archive_path}")"
  tar -czf "${archive_path}" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
fi

drift_verdict="$(
  python3 - <<'PY' "${drift_audit_json}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("verdict", "FAIL"))
PY
)"

echo
echo "Done:"
if [[ "${run_precheck}" == "1" ]]; then
  echo "  ${current_dir}-precheck/OBSERVATION_PRECHECK.md"
fi
echo "  ${current_dir}/OBSERVATION_RESULT.md"
echo "  ${current_dir}/OBSERVATION_DIFF.md"
echo "  ${current_dir}/OBSERVATION_EVAL.md"
echo "  ${drift_audit_md}"
echo "  ${drift_audit_json}"
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${archive_path}"
fi
echo "READONLY_EXIT_STATUS=${readonly_status}"
echo "DRIFT_VERDICT=${drift_verdict}"

if [[ "${readonly_status}" != "0" ]]; then
  exit "${readonly_status}"
fi
if [[ "${drift_verdict}" != "PASS" ]]; then
  exit 1
fi
