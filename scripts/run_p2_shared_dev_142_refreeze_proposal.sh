#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_refreeze_proposal.sh [options]

Options:
  --env-file <path>        Observation env file
                           default: $HOME/.config/yuantus/p2-shared-dev.env
  --output-dir <path>      Result directory
                           default: ./tmp/p2-shared-dev-142-refreeze-proposal-<timestamp>
  --proposed-label <label> Proposed tracked baseline label
                           default: shared-dev-142-readonly-<today>
  --skip-precheck          Skip precheck in the nested candidate preview
  --no-archive             Do not write <OUTPUT_DIR>.tar.gz
  -h, --help               Show this help

Behavior:
  - validates the shared-dev observation env
  - delegates the preview capture to scripts/run_p2_shared_dev_142_refreeze_candidate.sh
  - continues even if the candidate preview exits non-zero
  - writes:
    - <OUTPUT_DIR>/REFREEZE_PROPOSAL.md
    - <OUTPUT_DIR>/refreeze_proposal.json
    - <OUTPUT_DIR>/proposal/<proposed-label>/*
EOF
}

default_env_file="${HOME}/.config/yuantus/p2-shared-dev.env"
timestamp="$(date +%Y%m%d-%H%M%S)"
today="$(date +%Y%m%d)"

env_file="${default_env_file}"
output_dir="./tmp/p2-shared-dev-142-refreeze-proposal-${timestamp}"
proposed_label="shared-dev-142-readonly-${today}"
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
    --proposed-label)
      require_value "$1" "${2:-}"
      proposed_label="$2"
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
candidate_preview_dir="${output_dir}/candidate-preview"
proposal_dir="${output_dir}/proposal"
proposal_md="${output_dir}/REFREEZE_PROPOSAL.md"
proposal_json="${output_dir}/refreeze_proposal.json"

echo "== Shared-dev 142 readonly refreeze proposal =="
echo "ENV_FILE=${env_file}"
echo "OUTPUT_DIR=${output_dir}"
echo "PROPOSED_LABEL=${proposed_label}"
echo "RUN_PRECHECK=${run_precheck}"
echo "ARCHIVE_RESULT=${archive_result}"
echo

bash scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "${env_file}"

candidate_args=(
  --env-file "${env_file}"
  --output-dir "${candidate_preview_dir}"
  --no-archive
)
if [[ "${run_precheck}" == "0" ]]; then
  candidate_args+=(--skip-precheck)
fi

candidate_status=0
if ! bash scripts/run_p2_shared_dev_142_refreeze_candidate.sh "${candidate_args[@]}"; then
  candidate_status=$?
  echo "Refreeze candidate preview exited with status ${candidate_status}; continuing to render formal proposal." >&2
fi

python3 scripts/render_p2_shared_dev_142_refreeze_proposal.py \
  "${candidate_preview_dir}" \
  --output-dir "${proposal_dir}" \
  --output-md "${proposal_md}" \
  --output-json "${proposal_json}" \
  --proposed-label "${proposed_label}"

proposal_ready="$(
  python3 - "${proposal_json}" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(1 if payload.get("proposal_ready") else 0)
PY
)"
proposal_kind="$(
  python3 - "${proposal_json}" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("decision", {}).get("kind", "unknown"))
PY
)"

if [[ "${archive_result}" == "1" ]]; then
  tar -czf "${output_dir}.tar.gz" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
fi

echo
echo "CANDIDATE_EXIT_STATUS=${candidate_status}"
echo "PROPOSAL_READY=${proposal_ready}"
echo "PROPOSAL_DECISION_KIND=${proposal_kind}"
echo "PROPOSED_LABEL=${proposed_label}"
echo "Done:"
echo "  ${candidate_preview_dir}/STABLE_READONLY_CANDIDATE.md"
echo "  ${proposal_md}"
echo "  ${proposal_json}"
echo "  ${proposal_dir}/${proposed_label}/OBSERVATION_RESULT.md"
echo "  ${proposal_dir}/${proposed_label}/OBSERVATION_EVAL.md"
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${output_dir}.tar.gz"
fi

if [[ "${proposal_ready}" != "1" ]]; then
  exit 1
fi
