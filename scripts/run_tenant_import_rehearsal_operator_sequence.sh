#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_tenant_import_rehearsal_operator_sequence.sh \
    --implementation-packet-json PATH \
    --artifact-prefix PREFIX \
    --backup-restore-owner OWNER \
    --rehearsal-window WINDOW \
    --rehearsal-executed-by OPERATOR \
    --evidence-reviewer REVIEWER \
    --date YYYY-MM-DD \
    --confirm-rehearsal \
    [--source-url-env NAME] \
    [--target-url-env NAME] \
    [--batch-size N]

Run the P3.4 operator sequence from precheck through evidence precheck.

This wrapper executes the real row-copy rehearsal against the non-production
source/target database URLs held in the named environment variables.
It does not print database URL values.
It does not build closeout archives, produce reviewer packets, or authorize cutover.
It does not enable runtime schema-per-tenant mode.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

implementation_packet_json=""
artifact_prefix=""
backup_restore_owner=""
rehearsal_window=""
rehearsal_executed_by=""
evidence_reviewer=""
evidence_date=""
source_url_env="SOURCE_DATABASE_URL"
target_url_env="TARGET_DATABASE_URL"
batch_size="500"
confirm_rehearsal=0

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
    --batch-size)
      batch_size="${2:?missing value for --batch-size}"
      shift 2
      ;;
    --confirm-rehearsal)
      confirm_rehearsal=1
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

if [[ -z "${!source_url_env:-}" || -z "${!target_url_env:-}" ]]; then
  echo "error: source/target database URL environment variables must be set" >&2
  echo "missing or empty: $source_url_env or $target_url_env" >&2
  exit 2
fi

if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
else
  python_bin="python"
fi

operator_packet_json="${artifact_prefix}_operator_execution_packet.json"
operator_packet_md="${artifact_prefix}_operator_execution_packet.md"
operator_flow_prefix="${artifact_prefix}_operator_flow"
operator_launchpack_json="${artifact_prefix}_operator_launchpack.json"
operator_launchpack_md="${artifact_prefix}_operator_launchpack.md"
rehearsal_json="${artifact_prefix}_import_rehearsal.json"
rehearsal_md="${artifact_prefix}_import_rehearsal.md"
operator_evidence_template_json="${artifact_prefix}_operator_rehearsal_evidence_template.json"
operator_evidence_md="${artifact_prefix}_operator_rehearsal_evidence.md"
evidence_json="${artifact_prefix}_import_rehearsal_evidence.json"
evidence_md="${artifact_prefix}_import_rehearsal_evidence.md"

"$repo_root/scripts/precheck_tenant_import_rehearsal_operator.sh" \
  --artifact-prefix "$artifact_prefix" \
  --source-url-env "$source_url_env" \
  --target-url-env "$target_url_env"

"$repo_root/scripts/run_tenant_import_operator_launchpack.sh" \
  --implementation-packet-json "$implementation_packet_json" \
  --artifact-prefix "$artifact_prefix" \
  --operator-packet-json "$operator_packet_json" \
  --operator-packet-md "$operator_packet_md" \
  --flow-artifact-prefix "$operator_flow_prefix" \
  --output-json "$operator_launchpack_json" \
  --output-md "$operator_launchpack_md" \
  --source-url-env "$source_url_env" \
  --target-url-env "$target_url_env"

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" \
  -m yuantus.scripts.tenant_import_rehearsal \
  --implementation-packet-json "$implementation_packet_json" \
  --source-url "${!source_url_env}" \
  --target-url "${!target_url_env}" \
  --output-json "$rehearsal_json" \
  --output-md "$rehearsal_md" \
  --batch-size "$batch_size" \
  --confirm-rehearsal \
  --strict

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" \
  -m yuantus.scripts.tenant_import_rehearsal_evidence_template \
  --rehearsal-json "$rehearsal_json" \
  --backup-restore-owner "$backup_restore_owner" \
  --rehearsal-window "$rehearsal_window" \
  --rehearsal-executed-by "$rehearsal_executed_by" \
  --rehearsal-result pass \
  --evidence-reviewer "$evidence_reviewer" \
  --date "$evidence_date" \
  --output-json "$operator_evidence_template_json" \
  --output-md "$operator_evidence_md" \
  --strict

"$repo_root/scripts/precheck_tenant_import_rehearsal_evidence.sh" \
  --rehearsal-json "$rehearsal_json" \
  --implementation-packet-json "$implementation_packet_json" \
  --operator-evidence-md "$operator_evidence_md" \
  --artifact-prefix "$artifact_prefix" \
  --output-json "$evidence_json" \
  --output-md "$evidence_md"

echo
echo "P3.4 tenant import rehearsal operator sequence complete"
echo "Operator launchpack JSON: $operator_launchpack_json"
echo "Rehearsal JSON: $rehearsal_json"
echo "Operator evidence MD: $operator_evidence_md"
echo "Evidence JSON: $evidence_json"
echo "Ready for evidence closeout: true"
echo "Ready for cutover: false"
