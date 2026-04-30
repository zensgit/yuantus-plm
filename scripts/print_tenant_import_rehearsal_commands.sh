#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/print_tenant_import_rehearsal_commands.sh \
    --artifact-prefix PREFIX \
    [--source-url-env NAME] \
    [--target-url-env NAME]

Print the P3.4 tenant import rehearsal command sequence for an operator.

This helper prints commands only. It does not execute them, read database URL
values, connect to databases, accept evidence, build archives, or authorize
cutover.

Inputs:

  --artifact-prefix PREFIX   Required. Example: output/tenant_acme
  --source-url-env NAME      Optional. Default: SOURCE_DATABASE_URL
  --target-url-env NAME      Optional. Default: TARGET_DATABASE_URL

The generated commands assume the upstream implementation packet exists at:

  PREFIX_importer_implementation_packet.json
USAGE
}

artifact_prefix=""
source_url_env="SOURCE_DATABASE_URL"
target_url_env="TARGET_DATABASE_URL"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact-prefix)
      artifact_prefix="${2:?missing value for --artifact-prefix}"
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

if [[ -z "$artifact_prefix" ]]; then
  echo "error: --artifact-prefix is required" >&2
  usage >&2
  exit 2
fi

implementation_packet_json="${artifact_prefix}_importer_implementation_packet.json"
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

cat <<COMMANDS
# P3.4 tenant import rehearsal operator commands
#
# Prerequisites:
# - Real non-production PostgreSQL rehearsal DSNs are available.
# - ${source_url_env} and ${target_url_env} are exported in the shell.
# - ${implementation_packet_json} exists and is green.
# - Do not paste secret URL values into tracked files or chat.

test -n "\${${source_url_env}:-}" || { echo "missing ${source_url_env}" >&2; exit 2; }
test -n "\${${target_url_env}:-}" || { echo "missing ${target_url_env}" >&2; exit 2; }

scripts/run_tenant_import_operator_launchpack.sh \\
  --implementation-packet-json ${implementation_packet_json} \\
  --artifact-prefix ${artifact_prefix} \\
  --operator-packet-json ${operator_packet_json} \\
  --operator-packet-md ${operator_packet_md} \\
  --flow-artifact-prefix ${operator_flow_prefix} \\
  --output-json ${operator_launchpack_json} \\
  --output-md ${operator_launchpack_md}

PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \\
  --implementation-packet-json ${implementation_packet_json} \\
  --source-url "\$${source_url_env}" \\
  --target-url "\$${target_url_env}" \\
  --output-json ${rehearsal_json} \\
  --output-md ${rehearsal_md} \\
  --confirm-rehearsal

PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \\
  --rehearsal-json ${rehearsal_json} \\
  --backup-restore-owner "<owner>" \\
  --rehearsal-window "<window>" \\
  --rehearsal-executed-by "<operator>" \\
  --rehearsal-result pass \\
  --evidence-reviewer "<reviewer>" \\
  --evidence-date "<YYYY-MM-DD>" \\
  --output-json ${operator_evidence_template_json} \\
  --output-md ${operator_evidence_md}

# Review and complete ${operator_evidence_md} before running the evidence gate.

PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence \\
  --rehearsal-json ${rehearsal_json} \\
  --implementation-packet-json ${implementation_packet_json} \\
  --operator-evidence-md ${operator_evidence_md} \\
  --output-json ${evidence_json} \\
  --output-md ${evidence_md} \\
  --strict

scripts/run_tenant_import_evidence_closeout.sh \\
  --evidence-json ${evidence_json} \\
  --operator-packet-json ${operator_packet_json} \\
  --operator-evidence-template-json ${operator_evidence_template_json} \\
  --artifact-prefix ${artifact_prefix}
COMMANDS
