#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/validate_tenant_import_rehearsal_operator_commands.sh --command-file PATH

Options:
  --command-file PATH  Generated operator command file to validate.
  -h, --help           Show this help.

Validate a generated P3.4 tenant import operator command file without executing
it. The validator checks shell syntax, required command steps, and forbidden
secret/cutover patterns. It does not connect to databases, run row-copy, or does not print database URL values.
USAGE
}

command_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --command-file)
      command_file="${2:?missing value for --command-file}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$command_file" ]]; then
  echo "error: --command-file is required" >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$command_file" ]]; then
  echo "error: command file does not exist: $command_file" >&2
  exit 2
fi

failures=()

syntax_output="$(bash -n "$command_file" 2>&1)" || {
  failures+=("shell syntax failed")
  if [[ -n "$syntax_output" ]]; then
    failures+=("$syntax_output")
  fi
}

require_pattern() {
  local pattern="$1"
  if ! grep -Fq -- "$pattern" "$command_file"; then
    failures+=("missing required command pattern: $pattern")
  fi
}

first_line_for_pattern() {
  local pattern="$1"
  local line
  line="$(grep -nF -m 1 -- "$pattern" "$command_file" | cut -d: -f1 || true)"
  if [[ -z "$line" ]]; then
    echo "0"
  else
    echo "$line"
  fi
}

require_ordered_sequence() {
  local previous_label=""
  local previous_line=0
  local label
  local pattern
  local line

  local -a labels=(
    "env template generation"
    "env file precheck"
    "env export start"
    "env export end"
    "operator launchpack"
    "row-copy rehearsal"
    "evidence template"
    "evidence gate"
    "evidence closeout"
  )
  local -a patterns=(
    "scripts/generate_tenant_import_rehearsal_env_template.sh"
    "scripts/precheck_tenant_import_rehearsal_env_file.sh"
    "set -a"
    "set +a"
    "scripts/run_tenant_import_operator_launchpack.sh"
    "python -m yuantus.scripts.tenant_import_rehearsal \\"
    "python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \\"
    "python -m yuantus.scripts.tenant_import_rehearsal_evidence \\"
    "scripts/run_tenant_import_evidence_closeout.sh"
  )

  for i in "${!patterns[@]}"; do
    label="${labels[$i]}"
    pattern="${patterns[$i]}"
    line="$(first_line_for_pattern "$pattern")"
    if [[ "$line" -eq 0 ]]; then
      continue
    fi
    if [[ "$previous_line" -ne 0 && "$line" -le "$previous_line" ]]; then
      failures+=("command step out of order: $label must appear after $previous_label")
    fi
    previous_label="$label"
    previous_line="$line"
  done
}

forbid_pattern() {
  local pattern="$1"
  if grep -Fq -- "$pattern" "$command_file"; then
    failures+=("forbidden command pattern present: $pattern")
  fi
}

require_pattern "scripts/generate_tenant_import_rehearsal_env_template.sh"
require_pattern "scripts/precheck_tenant_import_rehearsal_env_file.sh"
require_pattern "set -a"
require_pattern "set +a"
require_pattern "scripts/run_tenant_import_operator_launchpack.sh"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal \\"
require_pattern '--source-url "$'
require_pattern '--target-url "$'
require_pattern "--confirm-rehearsal"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \\"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal_evidence \\"
require_pattern "--strict"
require_pattern "scripts/run_tenant_import_evidence_closeout.sh"

require_ordered_sequence

forbid_pattern "postgresql://"
forbid_pattern "postgresql+"
forbid_pattern "ready_for_cutover=true"
forbid_pattern "Ready for cutover: true"
forbid_pattern "TENANCY_MODE="
forbid_pattern "gh pr merge"
forbid_pattern "gh pr create"
forbid_pattern "curl "
forbid_pattern "psql "
forbid_pattern 'echo "$'
forbid_pattern 'printf "$'
forbid_pattern "printenv "
forbid_pattern "env |"

echo "P3.4 tenant import operator command file validation"
echo
echo "Command file: $command_file"
echo "Database URL values hidden: true"
echo

if [[ "${#failures[@]}" -eq 0 ]]; then
  echo "Ordered command sequence: true"
  echo "Ready for operator command execution: true"
  echo "Ready for cutover: false"
  exit 0
fi

echo "Ready for operator command execution: false"
echo "Ready for cutover: false"
echo
echo "Blockers:"
for failure in "${failures[@]}"; do
  echo "- $failure"
done
exit 1
