#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_readonly_rerun.sh [options]

Options:
  --env-file <path>         Observation env file
                            default: $HOME/.config/yuantus/p2-shared-dev.env
  --output-dir <path>       Result directory
                            default: ./tmp/p2-shared-dev-observation-142-readonly-rerun-<timestamp>
  --baseline-dir <path>     Baseline directory for readonly compare/eval
                            default: ./tmp/p2-shared-dev-observation-20260421-stable
                            tracked fallback dir: ./artifacts/p2-observation/shared-dev-142-readonly-20260421
  --baseline-archive <path> Baseline archive used only when the canonical baseline dir is missing
                            default: ./tmp/p2-shared-dev-observation-20260421-stable.tar.gz
  --baseline-label <label>  Baseline label for OBSERVATION_DIFF.md
                            default: shared-dev-142-readonly-20260421
  --skip-precheck           Skip precheck and run readonly rerun directly
  --no-restore              Do not auto-restore the canonical baseline dir from the canonical archive
  --no-archive              Do not write <OUTPUT_DIR>.tar.gz
  -h, --help                Show this help

Behavior:
  - validates $HOME/.config/yuantus/p2-shared-dev.env or the env file you pass
  - uses the current official shared-dev 142 readonly baseline
  - if the canonical baseline dir is missing and the canonical archive exists, restores it under ./tmp
  - runs precheck into <OUTPUT_DIR>-precheck unless --skip-precheck
  - if baseline_policy.json says overdue-only-stable, captures raw current under <OUTPUT_DIR>/raw-current,
    then renders the effective stable current into <OUTPUT_DIR> before readonly compare/eval
  - otherwise runs run_p2_observation_regression.sh directly with BASELINE_DIR, EVAL_MODE=readonly,
    and ARCHIVE_RESULT=1 by default
EOF
}

default_env_file="${HOME}/.config/yuantus/p2-shared-dev.env"
default_baseline_dir="./tmp/p2-shared-dev-observation-20260421-stable"
default_baseline_archive="./tmp/p2-shared-dev-observation-20260421-stable.tar.gz"
default_tracked_baseline_dir="./artifacts/p2-observation/shared-dev-142-readonly-20260421"
default_baseline_label="shared-dev-142-readonly-20260421"
timestamp="$(date +%Y%m%d-%H%M%S)"

env_file="${default_env_file}"
output_dir="./tmp/p2-shared-dev-observation-142-readonly-rerun-${timestamp}"
baseline_dir="${default_baseline_dir}"
baseline_archive="${default_baseline_archive}"
baseline_label="${default_baseline_label}"
run_precheck="1"
allow_restore="1"
archive_result="1"

read_baseline_policy_kind() {
  local policy_file="${baseline_dir}/baseline_policy.json"
  if [[ ! -f "${policy_file}" ]]; then
    echo "exact"
    return 0
  fi

  python3 - <<'PY' "${policy_file}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
kind = payload.get("kind")
if not isinstance(kind, str) or not kind:
    raise SystemExit("baseline_policy.json must contain a non-empty string kind")
print(kind)
PY
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "${value}" ]]; then
    echo "Missing value for ${flag}" >&2
    usage >&2
    exit 1
  fi
}

restore_canonical_baseline_if_missing() {
  if [[ -d "${baseline_dir}" ]]; then
    return 0
  fi

  if [[ "${allow_restore}" != "1" ]]; then
    echo "Missing baseline dir: ${baseline_dir}" >&2
    exit 1
  fi

  if [[ "${baseline_dir}" != "${default_baseline_dir}" ]]; then
    echo "Missing custom baseline dir: ${baseline_dir}" >&2
    echo "Auto-restore only supports the canonical shared-dev 142 baseline dir." >&2
    exit 1
  fi

  if [[ ! -f "${baseline_archive}" ]]; then
    if [[ -d "${default_tracked_baseline_dir}" ]]; then
      mkdir -p "$(dirname "${baseline_dir}")"
      rm -rf "${baseline_dir}"
      cp -R "${default_tracked_baseline_dir}" "${baseline_dir}"

      if [[ ! -d "${baseline_dir}" ]]; then
        echo "Tracked repo baseline restore completed but directory still missing: ${baseline_dir}" >&2
        exit 1
      fi

      echo "Restored canonical baseline dir from tracked repo baseline:"
      echo "  ${default_tracked_baseline_dir}"
      return 0
    fi

    echo "Missing baseline dir, archive, and tracked repo baseline: ${baseline_dir} / ${baseline_archive} / ${default_tracked_baseline_dir}" >&2
    exit 1
  fi

  mkdir -p "$(dirname "${baseline_dir}")"
  tar -xzf "${baseline_archive}" -C "$(dirname "${baseline_dir}")"

  if [[ ! -d "${baseline_dir}" ]]; then
    echo "Baseline restore completed but directory still missing: ${baseline_dir}" >&2
    exit 1
  fi

  echo "Restored canonical baseline dir from archive:"
  echo "  ${baseline_archive}"
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
precheck_output_dir="${output_dir}-precheck"

echo "== Shared-dev 142 readonly rerun =="
echo "ENV_FILE=${env_file}"
echo "BASELINE_DIR=${baseline_dir}"
echo "BASELINE_ARCHIVE=${baseline_archive}"
echo "BASELINE_LABEL=${baseline_label}"
echo "OUTPUT_DIR=${output_dir}"
echo "RUN_PRECHECK=${run_precheck}"
echo "ARCHIVE_RESULT=${archive_result}"
echo

bash scripts/validate_p2_shared_dev_env.sh \
  --mode observation \
  --observation-env "${env_file}"

restore_canonical_baseline_if_missing
baseline_policy_kind="$(read_baseline_policy_kind)"

echo "BASELINE_POLICY_KIND=${baseline_policy_kind}"

if [[ "${run_precheck}" == "1" ]]; then
  OUTPUT_DIR="${precheck_output_dir}" \
  ENVIRONMENT="shared-dev-142-readonly-precheck" \
  bash scripts/precheck_p2_observation_regression.sh \
    --env-file "${env_file}"
fi

if [[ "${baseline_policy_kind}" == "overdue-only-stable" ]]; then
  raw_current_dir="${output_dir}/raw-current"

  CURRENT_LABEL="raw-current" \
  EVAL_MODE="current-only" \
  ENVIRONMENT="shared-dev-142-readonly-raw-current" \
  ARCHIVE_RESULT="0" \
  OUTPUT_DIR="${raw_current_dir}" \
  bash scripts/run_p2_observation_regression.sh \
    --env-file "${env_file}"

  python3 scripts/render_p2_shared_dev_142_stable_current.py \
    "${raw_current_dir}" \
    --output-dir "${output_dir}" \
    --output-md "${output_dir}/STABLE_CURRENT_TRANSFORM.md" \
    --output-json "${output_dir}/stable_current_transform.json" \
    --environment "shared-dev-142-readonly" \
    --operator "${USER:-system}"

  python3 scripts/compare_p2_observation_results.py \
    "${baseline_dir}" \
    "${output_dir}" \
    --baseline-label "${baseline_label}" \
    --current-label "current-rerun"

  python3 scripts/evaluate_p2_observation_results.py \
    "${output_dir}" \
    --mode readonly \
    --baseline-dir "${baseline_dir}" \
    --output "${output_dir}/OBSERVATION_EVAL.md"

  if [[ "${archive_result}" == "1" ]]; then
    mkdir -p "$(dirname "${output_dir}.tar.gz")"
    tar -czf "${output_dir}.tar.gz" -C "$(dirname "${output_dir}")" "$(basename "${output_dir}")"
  fi
else
  BASELINE_DIR="${baseline_dir}" \
  BASELINE_LABEL="${baseline_label}" \
  CURRENT_LABEL="current-rerun" \
  EVAL_MODE="readonly" \
  ENVIRONMENT="shared-dev-142-readonly" \
  ARCHIVE_RESULT="${archive_result}" \
  OUTPUT_DIR="${output_dir}" \
  bash scripts/run_p2_observation_regression.sh \
    --env-file "${env_file}"
fi

echo
echo "Done:"
if [[ "${run_precheck}" == "1" ]]; then
  echo "  ${precheck_output_dir}/OBSERVATION_PRECHECK.md"
fi
if [[ "${baseline_policy_kind}" == "overdue-only-stable" ]]; then
  echo "  ${output_dir}/raw-current/OBSERVATION_RESULT.md"
  echo "  ${output_dir}/STABLE_CURRENT_TRANSFORM.md"
  echo "  ${output_dir}/stable_current_transform.json"
fi
echo "  ${output_dir}/OBSERVATION_RESULT.md"
echo "  ${output_dir}/OBSERVATION_DIFF.md"
echo "  ${output_dir}/OBSERVATION_EVAL.md"
if [[ "${archive_result}" == "1" ]]; then
  echo "  ${output_dir}.tar.gz"
fi
