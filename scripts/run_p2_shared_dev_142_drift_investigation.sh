#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_drift_investigation.sh [options]

Options:
  --env-file <path>           Observation env file
                              default: $HOME/.config/yuantus/p2-shared-dev.env
  --output-dir <path>         Output root
                              default: ./tmp/p2-shared-dev-142-drift-investigation-<timestamp>
  --baseline-dir <path>       Baseline directory for readonly compare/eval
                              default: ./tmp/p2-shared-dev-observation-20260421-stable
  --baseline-archive <path>   Baseline archive used only when the canonical baseline dir is missing
                              default: ./tmp/p2-shared-dev-observation-20260421-stable.tar.gz
  --baseline-label <label>    Baseline label for readonly compare/eval
                              default: shared-dev-142-readonly-20260421
  --current-label <label>     Current label used in the nested drift audit
                              default: current-drift-audit
  --skip-precheck             Skip precheck inside nested readonly rerun
  --no-restore                Do not auto-restore the canonical baseline dir from the canonical archive
  --no-archive                Do not write <OUTPUT_DIR>.tar.gz
  -h, --help                  Show help

Behavior:
  - runs scripts/run_p2_shared_dev_142_drift_audit.sh into <OUTPUT_DIR>/drift-audit
  - renders:
    - <OUTPUT_DIR>/DRIFT_INVESTIGATION.md
    - <OUTPUT_DIR>/drift_investigation.json
  - preserves the nested drift verdict while still producing the investigation evidence pack

Boundary:
  - this is investigation-only; it does not refreeze the baseline
  - use it when you need a fixed evidence pack before deciding whether to refreeze or keep digging
EOF
}

default_env_file="${HOME}/.config/yuantus/p2-shared-dev.env"
default_baseline_dir="./tmp/p2-shared-dev-observation-20260421-stable"
default_baseline_archive="./tmp/p2-shared-dev-observation-20260421-stable.tar.gz"
default_baseline_label="shared-dev-142-readonly-20260421"
default_current_label="current-drift-audit"
timestamp="$(date +%Y%m%d-%H%M%S)"

env_file="${default_env_file}"
output_dir="./tmp/p2-shared-dev-142-drift-investigation-${timestamp}"
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
drift_audit_dir="${output_dir}/drift-audit"
investigation_md="${output_dir}/DRIFT_INVESTIGATION.md"
investigation_json="${output_dir}/drift_investigation.json"
archive_path="${output_dir}.tar.gz"

echo "== Shared-dev 142 drift investigation =="
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

drift_cmd=(
  bash scripts/run_p2_shared_dev_142_drift_audit.sh
  --env-file "${env_file}"
  --output-dir "${drift_audit_dir}"
  --baseline-dir "${baseline_dir}"
  --baseline-archive "${baseline_archive}"
  --baseline-label "${baseline_label}"
  --current-label "${current_label}"
  --no-archive
)

if [[ "${run_precheck}" != "1" ]]; then
  drift_cmd+=(--skip-precheck)
fi
if [[ "${allow_restore}" != "1" ]]; then
  drift_cmd+=(--no-restore)
fi

drift_status="0"
if "${drift_cmd[@]}"; then
  drift_status="0"
else
  drift_status="$?"
  echo "Drift audit exited with status ${drift_status}; continuing to render investigation pack." >&2
fi

python3 scripts/render_p2_shared_dev_142_drift_investigation.py \
  "${drift_audit_dir}" \
  --output-md "${investigation_md}" \
  --output-json "${investigation_json}"

if [[ "${archive_result}" == "1" ]]; then
  mkdir -p "$(dirname "${archive_path}")"
  tar -czf "${archive_path}" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
fi

investigation_verdict="$(
  python3 - <<'PY' "${investigation_json}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("verdict", "FAIL"))
PY
)"

investigation_classification="$(
  python3 - <<'PY' "${investigation_json}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("classification", "unknown"))
PY
)"

echo
echo "Done:"
echo "  ${drift_audit_dir}/DRIFT_AUDIT.md"
echo "  ${drift_audit_dir}/drift_audit.json"
echo "  ${investigation_md}"
echo "  ${investigation_json}"
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${archive_path}"
fi
echo "DRIFT_AUDIT_EXIT_STATUS=${drift_status}"
echo "INVESTIGATION_VERDICT=${investigation_verdict}"
echo "INVESTIGATION_CLASSIFICATION=${investigation_classification}"

if [[ "${drift_status}" != "0" ]]; then
  exit "${drift_status}"
fi
if [[ "${investigation_verdict}" != "PASS" ]]; then
  exit 1
fi
