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
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal"
require_pattern "--confirm-rehearsal"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal_evidence_template"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal_evidence"
require_pattern "--strict"
require_pattern "scripts/run_tenant_import_evidence_closeout.sh"

forbid_pattern "postgresql://"
forbid_pattern "postgresql+"
forbid_pattern "ready_for_cutover=true"
forbid_pattern "Ready for cutover: true"
forbid_pattern "TENANCY_MODE="
forbid_pattern "gh pr merge"
forbid_pattern "gh pr create"
forbid_pattern "curl "
forbid_pattern "psql "

echo "P3.4 tenant import operator command file validation"
echo
echo "Command file: $command_file"
echo "Database URL values hidden: true"
echo

if [[ "${#failures[@]}" -eq 0 ]]; then
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
