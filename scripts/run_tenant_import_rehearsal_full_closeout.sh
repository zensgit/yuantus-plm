#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_tenant_import_rehearsal_full_closeout.sh \
    --implementation-packet-json PATH \
    --artifact-prefix PREFIX \
    --backup-restore-owner OWNER \
    --rehearsal-window WINDOW \
    --rehearsal-executed-by OPERATOR \
    --evidence-reviewer REVIEWER \
    --date YYYY-MM-DD \
    --confirm-rehearsal \
    --confirm-closeout \
    [--source-url-env NAME] \
    [--target-url-env NAME] \
    [--env-file PATH] \
    [--batch-size N]

Run the P3.4 operator rehearsal sequence and evidence closeout in one explicit
operator command.

This wrapper executes the real non-production row-copy rehearsal through the
operator-sequence wrapper, then runs the DB-free evidence closeout chain. It
does not print database URL values, authorize cutover, or enable runtime
schema-per-tenant mode.

It can load source/target database URL variables from --env-file without
printing their values. Keep that file outside the repository, for example
$HOME/.config/yuantus/tenant-import-rehearsal.env.
USAGE
}

implementation_packet_json=""
artifact_prefix=""
backup_restore_owner=""
rehearsal_window=""
rehearsal_executed_by=""
evidence_reviewer=""
evidence_date=""
source_url_env="SOURCE_DATABASE_URL"
target_url_env="TARGET_DATABASE_URL"
env_file=""
batch_size="500"
confirm_rehearsal=0
confirm_closeout=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --implementation-packet-json)
      implementation_packet_json="${2:?missing value for --implementation-packet-json}"
      shift 2
      ;;
    --artifact-prefix)
      artifact_prefix="${2:?missing value for --artifact-prefix}"
      shift 2
      ;;
    --backup-restore-owner)
      backup_restore_owner="${2:?missing value for --backup-restore-owner}"
      shift 2
      ;;
    --rehearsal-window)
      rehearsal_window="${2:?missing value for --rehearsal-window}"
      shift 2
      ;;
    --rehearsal-executed-by)
      rehearsal_executed_by="${2:?missing value for --rehearsal-executed-by}"
      shift 2
      ;;
    --evidence-reviewer)
      evidence_reviewer="${2:?missing value for --evidence-reviewer}"
      shift 2
      ;;
    --date)
      evidence_date="${2:?missing value for --date}"
      shift 2
      ;;
    --source-url-env)
      source_url_env="${2:?missing value for --source-url-env}"
      shift 2
      ;;
    --target-url-env)
      target_url_env="${2:?missing value for --target-url-env}"
      shift 2
      ;;
    --env-file)
      env_file="${2:?missing value for --env-file}"
      shift 2
      ;;
    --batch-size)
      batch_size="${2:?missing value for --batch-size}"
      shift 2
      ;;
    --confirm-rehearsal)
      confirm_rehearsal=1
      shift
      ;;
    --confirm-closeout)
      confirm_closeout=1
      shift
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

validate_env_var_name() {
  local option="$1"
  local name="$2"

  if [[ ! "$name" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
    echo "error: $option must be an uppercase shell environment variable name ([A-Z_][A-Z0-9_]*)" >&2
    return 2
  fi
}

if [[ -z "$implementation_packet_json" || -z "$artifact_prefix" ]]; then
  echo "error: --implementation-packet-json and --artifact-prefix are required" >&2
  usage >&2
  exit 2
fi

if [[ -z "$backup_restore_owner" || -z "$rehearsal_window" || -z "$rehearsal_executed_by" || -z "$evidence_reviewer" || -z "$evidence_date" ]]; then
  echo "error: backup owner, window, operator, reviewer, and date are required" >&2
  usage >&2
  exit 2
fi

if [[ "$confirm_rehearsal" -ne 1 ]]; then
  echo "error: --confirm-rehearsal is required for row-copy execution" >&2
  usage >&2
  exit 2
fi

if [[ "$confirm_closeout" -ne 1 ]]; then
  echo "error: --confirm-closeout is required for evidence closeout" >&2
  usage >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

validate_env_var_name "--source-url-env" "$source_url_env"
validate_env_var_name "--target-url-env" "$target_url_env"

if [[ -n "$env_file" ]]; then
  "$repo_root/scripts/precheck_tenant_import_rehearsal_env_file.sh" \
    --env-file "$env_file" \
    --source-url-env "$source_url_env" \
    --target-url-env "$target_url_env"
else
  "$repo_root/scripts/precheck_tenant_import_rehearsal_env_file.sh" \
    --source-url-env "$source_url_env" \
    --target-url-env "$target_url_env"
fi

if [[ -n "$env_file" ]]; then
  if [[ ! -f "$env_file" ]]; then
    echo "error: --env-file does not exist: $env_file" >&2
    exit 2
  fi
  set -a
  # shellcheck disable=SC1090
  . "$env_file"
  set +a
fi

operator_packet_json="${artifact_prefix}_operator_execution_packet.json"
operator_evidence_template_json="${artifact_prefix}_operator_rehearsal_evidence_template.json"
evidence_json="${artifact_prefix}_import_rehearsal_evidence.json"
reviewer_packet_json="${artifact_prefix}_reviewer_packet.json"

"$repo_root/scripts/run_tenant_import_rehearsal_operator_sequence.sh" \
  --implementation-packet-json "$implementation_packet_json" \
  --artifact-prefix "$artifact_prefix" \
  --backup-restore-owner "$backup_restore_owner" \
  --rehearsal-window "$rehearsal_window" \
  --rehearsal-executed-by "$rehearsal_executed_by" \
  --evidence-reviewer "$evidence_reviewer" \
  --date "$evidence_date" \
  --source-url-env "$source_url_env" \
  --target-url-env "$target_url_env" \
  --batch-size "$batch_size" \
  --confirm-rehearsal

"$repo_root/scripts/run_tenant_import_evidence_closeout.sh" \
  --evidence-json "$evidence_json" \
  --operator-packet-json "$operator_packet_json" \
  --operator-evidence-template-json "$operator_evidence_template_json" \
  --artifact-prefix "$artifact_prefix"

echo
echo "P3.4 tenant import rehearsal full closeout complete"
echo "Evidence JSON: $evidence_json"
echo "Reviewer packet JSON: $reviewer_packet_json"
echo "Ready for reviewer packet: true"
echo "Ready for cutover: false"
