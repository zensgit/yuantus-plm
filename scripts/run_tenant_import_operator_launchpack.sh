#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_tenant_import_operator_launchpack.sh \
    --implementation-packet-json PATH \
    --artifact-prefix PREFIX \
    [--operator-packet-json PATH] \
    [--operator-packet-md PATH] \
    [--flow-artifact-prefix PREFIX] \
    [--output-json PATH] \
    [--output-md PATH] \
    [--source-url-env NAME] \
    [--target-url-env NAME] \
    [--no-strict]

Build the DB-free P3.4 tenant import operator launchpack from a green
implementation packet. This wrapper only delegates to:

  python -m yuantus.scripts.tenant_import_rehearsal_operator_launchpack

Defaults derived from --artifact-prefix PREFIX:

  --operator-packet-json PREFIX_operator_execution_packet.json
  --operator-packet-md   PREFIX_operator_execution_packet.md
  --flow-artifact-prefix PREFIX_operator_flow
  --output-json          PREFIX_operator_launchpack.json
  --output-md            PREFIX_operator_launchpack.md

The wrapper is strict by default and returns non-zero when the launchpack is
blocked. Use --no-strict only when intentionally generating a blocked report.

Safety boundary:

  - reads local JSON artifacts only;
  - writes local JSON/Markdown artifacts only;
  - does not open database connections;
  - does not run row-copy rehearsal;
  - does not accept operator evidence;
  - does not build a cutover archive;
  - never authorizes production cutover.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

implementation_packet_json=""
artifact_prefix=""
operator_packet_json=""
operator_packet_md=""
flow_artifact_prefix=""
output_json=""
output_md=""
source_url_env="SOURCE_DATABASE_URL"
target_url_env="TARGET_DATABASE_URL"
strict=1

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
    --operator-packet-json)
      operator_packet_json="${2:?missing value for --operator-packet-json}"
      shift 2
      ;;
    --operator-packet-md)
      operator_packet_md="${2:?missing value for --operator-packet-md}"
      shift 2
      ;;
    --flow-artifact-prefix)
      flow_artifact_prefix="${2:?missing value for --flow-artifact-prefix}"
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
    --source-url-env)
      source_url_env="${2:?missing value for --source-url-env}"
      shift 2
      ;;
    --target-url-env)
      target_url_env="${2:?missing value for --target-url-env}"
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

operator_packet_json="${operator_packet_json:-${artifact_prefix}_operator_execution_packet.json}"
operator_packet_md="${operator_packet_md:-${artifact_prefix}_operator_execution_packet.md}"
flow_artifact_prefix="${flow_artifact_prefix:-${artifact_prefix}_operator_flow}"
output_json="${output_json:-${artifact_prefix}_operator_launchpack.json}"
output_md="${output_md:-${artifact_prefix}_operator_launchpack.md}"

if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
else
  python_bin="python"
fi

args=(
  -m yuantus.scripts.tenant_import_rehearsal_operator_launchpack
  --implementation-packet-json "$implementation_packet_json"
  --artifact-prefix "$artifact_prefix"
  --operator-packet-json "$operator_packet_json"
  --operator-packet-md "$operator_packet_md"
  --flow-artifact-prefix "$flow_artifact_prefix"
  --source-url-env "$source_url_env"
  --target-url-env "$target_url_env"
  --output-json "$output_json"
  --output-md "$output_md"
)

if [[ "$strict" -eq 1 ]]; then
  args+=(--strict)
fi

PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" "${args[@]}"
