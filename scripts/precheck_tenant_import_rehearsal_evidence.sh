#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/precheck_tenant_import_rehearsal_evidence.sh \
    --rehearsal-json PATH \
    --implementation-packet-json PATH \
    --operator-evidence-md PATH \
    --artifact-prefix PREFIX \
    [--output-json PATH] \
    [--output-md PATH] \
    [--no-strict]

Run the DB-free P3.4 operator-evidence precheck before evidence closeout.

Defaults derived from --artifact-prefix PREFIX:

  --output-json PREFIX_import_rehearsal_evidence.json
  --output-md   PREFIX_import_rehearsal_evidence.md

This helper validates local JSON/Markdown artifacts only. It does not print database URL values.
It does not connect to databases, execute row-copy, build archives, or authorize cutover.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rehearsal_json=""
implementation_packet_json=""
operator_evidence_md=""
artifact_prefix=""
output_json=""
output_md=""
strict=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rehearsal-json)
      rehearsal_json="${2:?missing value for --rehearsal-json}"
      shift 2
      ;;
    --implementation-packet-json)
      implementation_packet_json="${2:?missing value for --implementation-packet-json}"
      shift 2
      ;;
    --operator-evidence-md)
      operator_evidence_md="${2:?missing value for --operator-evidence-md}"
      shift 2
      ;;
    --artifact-prefix)
      artifact_prefix="${2:?missing value for --artifact-prefix}"
      shift 2
      ;;
    --output-json)
      output_json="${2:?missing value for --output-json}"
      shift 2
      ;;
    --output-md)
      output_md="${2:?missing value for --output-md}"
      shift 2
      ;;
    --no-strict)
      strict=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument" >&2
      echo "argument value hidden: true" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$rehearsal_json" || -z "$implementation_packet_json" || -z "$operator_evidence_md" || -z "$artifact_prefix" ]]; then
  echo "error: --rehearsal-json, --implementation-packet-json, --operator-evidence-md, and --artifact-prefix are required" >&2
  usage >&2
  exit 2
fi

output_json="${output_json:-${artifact_prefix}_import_rehearsal_evidence.json}"
output_md="${output_md:-${artifact_prefix}_import_rehearsal_evidence.md}"

if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
else
  python_bin="python"
fi

strict_args=()
if [[ "$strict" -eq 1 ]]; then
  strict_args=(--strict)
fi

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" \
  -m yuantus.scripts.tenant_import_rehearsal_evidence \
  --rehearsal-json "$rehearsal_json" \
  --implementation-packet-json "$implementation_packet_json" \
  --operator-evidence-md "$operator_evidence_md" \
  --output-json "$output_json" \
  --output-md "$output_md" \
  "${strict_args[@]}"

echo "P3.4 tenant import rehearsal evidence precheck"
echo
echo "Rehearsal JSON: $rehearsal_json"
echo "Implementation packet JSON: $implementation_packet_json"
echo "Operator evidence MD: $operator_evidence_md"
echo "Evidence JSON: $output_json"
echo "Evidence MD: $output_md"
echo "Ready for evidence closeout: true"
echo "Ready for cutover: false"
