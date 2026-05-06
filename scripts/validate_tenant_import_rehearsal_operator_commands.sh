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
    failures+=("shell syntax details hidden: true")
  fi
}

require_pattern() {
  local pattern="$1"
  if ! grep -Fq -- "$pattern" "$command_file"; then
    failures+=("missing required command pattern: $pattern")
  fi
}

require_url_env_reference() {
  local option="$1"
  local regex='^[[:space:]]*'"${option}"'[[:space:]]+"\$[A-Z_][A-Z0-9_]*"[[:space:]]*\\?[[:space:]]*$'

  if ! grep -Eq -- "$regex" "$command_file"; then
    failures+=("invalid ${option} environment variable reference; expected quoted uppercase env var reference")
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

line_has_forbidden_shell_control() {
  local line="$1"

  if [[ "$line" == *'$('* || "$line" == *'`'* || "$line" == *';'* || "$line" == *'&&'* || "$line" == *'||'* || "$line" == *'|'* ]]; then
    return 0
  fi
  return 1
}

strip_trailing_continuation() {
  local line="$1"

  if [[ "$line" == *'\' ]]; then
    line="${line%\\}"
  fi
  line="${line%"${line##*[![:space:]]}"}"
  printf '%s' "$line"
}

safe_path_token_regex='[-A-Za-z0-9_./:]+'
safe_quoted_metadata_regex='"[^"$`\\]+"'

option_allowed_for_command() {
  local command="$1"
  local line="$2"

  line="$(strip_trailing_continuation "$line")"

  case "$command" in
    env_template)
      [[ "$line" =~ ^--out[[:space:]]+\"[^\"]+\"$ ]]
      ;;
    env_precheck)
      [[ "$line" =~ ^--env-file[[:space:]]+\"[^\"]+\"$ || "$line" =~ ^--source-url-env[[:space:]]+[A-Z_][A-Z0-9_]*$ || "$line" =~ ^--target-url-env[[:space:]]+[A-Z_][A-Z0-9_]*$ ]]
      ;;
    launchpack)
      [[ "$line" =~ ^--(implementation-packet-json|artifact-prefix|operator-packet-json|operator-packet-md|flow-artifact-prefix|output-json|output-md)[[:space:]]+${safe_path_token_regex}$ ]]
      ;;
    row_copy)
      [[ "$line" =~ ^--implementation-packet-json[[:space:]]+${safe_path_token_regex}$ || "$line" =~ ^--source-url[[:space:]]+\"\$[A-Z_][A-Z0-9_]*\"$ || "$line" =~ ^--target-url[[:space:]]+\"\$[A-Z_][A-Z0-9_]*\"$ || "$line" =~ ^--output-json[[:space:]]+${safe_path_token_regex}$ || "$line" =~ ^--output-md[[:space:]]+${safe_path_token_regex}$ || "$line" == "--confirm-rehearsal" ]]
      ;;
    evidence_template)
      [[ "$line" =~ ^--rehearsal-json[[:space:]]+${safe_path_token_regex}$ || "$line" =~ ^--backup-restore-owner[[:space:]]+${safe_quoted_metadata_regex}$ || "$line" =~ ^--rehearsal-window[[:space:]]+${safe_quoted_metadata_regex}$ || "$line" =~ ^--rehearsal-executed-by[[:space:]]+${safe_quoted_metadata_regex}$ || "$line" == "--rehearsal-result pass" || "$line" =~ ^--evidence-reviewer[[:space:]]+${safe_quoted_metadata_regex}$ || "$line" =~ ^--evidence-date[[:space:]]+${safe_quoted_metadata_regex}$ || "$line" =~ ^--output-json[[:space:]]+${safe_path_token_regex}$ || "$line" =~ ^--output-md[[:space:]]+${safe_path_token_regex}$ ]]
      ;;
    evidence_gate)
      [[ "$line" =~ ^--(rehearsal-json|implementation-packet-json|operator-evidence-md|output-json|output-md)[[:space:]]+${safe_path_token_regex}$ || "$line" == "--strict" ]]
      ;;
    evidence_closeout)
      [[ "$line" =~ ^--(evidence-json|operator-packet-json|operator-evidence-template-json|artifact-prefix)[[:space:]]+${safe_path_token_regex}$ ]]
      ;;
    *)
      return 1
      ;;
  esac
}

validate_allowed_command_lines() {
  local line_number=0
  local line=""
  local trimmed=""
  local current_command=""

  while IFS= read -r line || [[ -n "$line" ]]; do
    line_number=$((line_number + 1))
    trimmed="${line#"${line%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"

    case "$trimmed" in
      ""|\#*)
        continue
        ;;
    esac

    if line_has_forbidden_shell_control "$trimmed"; then
      failures+=("forbidden shell control syntax on line $line_number")
      continue
    fi

    case "$trimmed" in
      "scripts/generate_tenant_import_rehearsal_env_template.sh \\")
        current_command="env_template"
        continue
        ;;
      "scripts/precheck_tenant_import_rehearsal_env_file.sh \\")
        current_command="env_precheck"
        continue
        ;;
      "scripts/run_tenant_import_operator_launchpack.sh \\")
        current_command="launchpack"
        continue
        ;;
      "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \\")
        current_command="row_copy"
        continue
        ;;
      "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \\")
        current_command="evidence_template"
        continue
        ;;
      "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence \\")
        current_command="evidence_gate"
        continue
        ;;
      "scripts/run_tenant_import_evidence_closeout.sh \\")
        current_command="evidence_closeout"
        continue
        ;;
      "set -a"|"set +a")
        if [[ -n "$current_command" ]]; then
          failures+=("unsupported command line $line_number; only generated tenant import commands are allowed")
        fi
        continue
        ;;
    esac

    if [[ "$trimmed" =~ ^\.[[:space:]]+\"[^\"]+\"$ ]]; then
      if [[ -n "$current_command" ]]; then
        failures+=("unsupported command line $line_number; only generated tenant import commands are allowed")
      fi
      continue
    fi

    if [[ "$trimmed" == --* ]]; then
      if [[ -z "$current_command" ]]; then
        failures+=("unsupported option line $line_number outside generated command step")
        continue
      fi
      if ! option_allowed_for_command "$current_command" "$trimmed"; then
        failures+=("unsupported option line $line_number for generated command step: $current_command")
        continue
      fi
      if [[ "$trimmed" != *'\' ]]; then
        current_command=""
      fi
      continue
    fi

    failures+=("unsupported command line $line_number; only generated tenant import commands are allowed")
  done < "$command_file"
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
require_url_env_reference "--source-url"
require_url_env_reference "--target-url"
require_pattern "--confirm-rehearsal"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \\"
require_pattern "python -m yuantus.scripts.tenant_import_rehearsal_evidence \\"
require_pattern "--strict"
require_pattern "scripts/run_tenant_import_evidence_closeout.sh"

require_ordered_sequence
validate_allowed_command_lines

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
