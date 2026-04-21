#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_p2_shared_dev_142_entrypoint.sh --mode <mode> [--dry-run] [-- <mode-specific args>]

Modes:
  readonly-rerun
      Direct local readonly rerun against the current official shared-dev 142 baseline.
  refreeze-readiness
      Direct local readonly rerun plus a readonly refreeze readiness decision pack.
  refreeze-candidate
      Direct local readonly rerun plus a stable readonly candidate preview that excludes future pending approvals.
  refreeze-proposal
      Direct local readonly rerun plus stable candidate preview plus a formal baseline-switch proposal pack.
  drift-audit
      Direct local readonly rerun plus drift summary against the current official shared-dev 142 baseline.
  drift-investigation
      Direct local readonly rerun plus drift summary plus investigation evidence pack.
  workflow-probe
      GitHub Actions current-only probe against shared-dev host 142.
  workflow-readonly-check
      GitHub Actions probe plus local readonly compare/eval against the official frozen baseline.
  print-readonly-commands
      Print the expanded readonly rerun commands for manual inspection/debugging.
  print-refreeze-readiness-commands
      Print the expanded readonly refreeze-readiness commands for manual inspection/debugging.
  print-refreeze-candidate-commands
      Print the expanded readonly refreeze-candidate preview commands for manual inspection/debugging.
  print-refreeze-proposal-commands
      Print the expanded readonly refreeze-proposal commands for manual inspection/debugging.
  print-drift-commands
      Print the expanded shared-dev 142 drift audit commands for manual inspection/debugging.
  print-investigation-commands
      Print the expanded shared-dev 142 drift investigation commands for manual inspection/debugging.

Options:
  --mode <mode>   Required. One of the modes above.
  --dry-run       Print the selected target script plus forwarded args and exit without executing.
  --              End wrapper args. Everything after this is forwarded to the selected target script.
  -h, --help      Show help.

Examples:
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode refreeze-readiness
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode refreeze-candidate
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode refreeze-proposal
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-audit
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode drift-investigation
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-probe -- --eco-state open
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check -- --eco-type ECR
  bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-readonly-commands

Boundary:
  - use this as the single selector for shared-dev host `142.171.239.56`
  - mode-specific details still live in the underlying target scripts
EOF
}

mode=""
dry_run="0"
passthrough=()

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
    --mode)
      require_value "$1" "${2:-}"
      mode="$2"
      shift 2
      ;;
    --dry-run)
      dry_run="1"
      shift
      ;;
    --)
      shift
      passthrough=("$@")
      break
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

if [[ -z "${mode}" ]]; then
  echo "Missing required --mode" >&2
  usage >&2
  exit 1
fi

target_script=""
mode_summary=""

case "${mode}" in
  readonly-rerun)
    target_script="scripts/run_p2_shared_dev_142_readonly_rerun.sh"
    mode_summary="direct local readonly rerun"
    ;;
  refreeze-readiness)
    target_script="scripts/run_p2_shared_dev_142_refreeze_readiness.sh"
    mode_summary="direct local readonly rerun plus refreeze readiness decision pack"
    ;;
  refreeze-candidate)
    target_script="scripts/run_p2_shared_dev_142_refreeze_candidate.sh"
    mode_summary="direct local readonly rerun plus stable readonly candidate preview"
    ;;
  refreeze-proposal)
    target_script="scripts/run_p2_shared_dev_142_refreeze_proposal.sh"
    mode_summary="direct local readonly rerun plus formal readonly refreeze proposal pack"
    ;;
  drift-audit)
    target_script="scripts/run_p2_shared_dev_142_drift_audit.sh"
    mode_summary="direct local readonly rerun plus drift audit summary"
    ;;
  drift-investigation)
    target_script="scripts/run_p2_shared_dev_142_drift_investigation.sh"
    mode_summary="direct local readonly rerun plus drift investigation evidence pack"
    ;;
  workflow-probe)
    target_script="scripts/run_p2_shared_dev_142_workflow_probe.sh"
    mode_summary="GitHub workflow current-only probe"
    ;;
  workflow-readonly-check)
    target_script="scripts/run_p2_shared_dev_142_workflow_readonly_check.sh"
    mode_summary="GitHub workflow probe plus local readonly compare/eval"
    ;;
  print-readonly-commands)
    target_script="scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh"
    mode_summary="expanded readonly rerun command printout"
    ;;
  print-refreeze-readiness-commands)
    target_script="scripts/print_p2_shared_dev_142_refreeze_readiness_commands.sh"
    mode_summary="expanded readonly refreeze-readiness command printout"
    ;;
  print-refreeze-candidate-commands)
    target_script="scripts/print_p2_shared_dev_142_refreeze_candidate_commands.sh"
    mode_summary="expanded readonly refreeze-candidate command printout"
    ;;
  print-refreeze-proposal-commands)
    target_script="scripts/print_p2_shared_dev_142_refreeze_proposal_commands.sh"
    mode_summary="expanded readonly refreeze-proposal command printout"
    ;;
  print-drift-commands)
    target_script="scripts/print_p2_shared_dev_142_drift_audit_commands.sh"
    mode_summary="expanded drift audit command printout"
    ;;
  print-investigation-commands)
    target_script="scripts/print_p2_shared_dev_142_drift_investigation_commands.sh"
    mode_summary="expanded drift investigation command printout"
    ;;
  *)
    echo "Unsupported --mode: ${mode}" >&2
    usage >&2
    exit 1
    ;;
esac

echo "== Shared-dev 142 entrypoint =="
echo "MODE=${mode}"
echo "SUMMARY=${mode_summary}"
echo "TARGET=${target_script}"
if [[ "${#passthrough[@]}" -eq 0 ]]; then
  echo "FORWARDED_ARGS=<none>"
else
  printf 'FORWARDED_ARGS='
  printf '%q ' "${passthrough[@]}"
  printf '\n'
fi

if [[ "${dry_run}" == "1" ]]; then
  echo "DRY_RUN=1"
  exit 0
fi

cmd=(bash "${target_script}")
if [[ "${#passthrough[@]}" -gt 0 ]]; then
  cmd+=("${passthrough[@]}")
fi

"${cmd[@]}"
