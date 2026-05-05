#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/prepare_tenant_import_rehearsal_operator_commands.sh \
    --artifact-prefix PREFIX \
    --output PATH \
    [--env-file PATH] \
    [--source-url-env NAME] \
    [--target-url-env NAME]

Run the DB-free P3.4 operator precheck, then write the operator command
sequence to PATH only if the precheck passes.

This helper does not print database URL values, connect to databases, execute
row-copy, accept evidence, build archives, or authorize cutover.
USAGE
}

artifact_prefix=""
output_path=""
env_file=""
source_url_env="SOURCE_DATABASE_URL"
target_url_env="TARGET_DATABASE_URL"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact-prefix)
      artifact_prefix="${2:?missing value for --artifact-prefix}"
      shift 2
      ;;
    --output)
      output_path="${2:?missing value for --output}"
      shift 2
      ;;
    --env-file)
      env_file="${2:?missing value for --env-file}"
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

if [[ -z "$artifact_prefix" || -z "$output_path" ]]; then
  echo "error: --artifact-prefix and --output are required" >&2
  usage >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
precheck_script="$repo_root/scripts/precheck_tenant_import_rehearsal_operator.sh"
env_precheck_script="$repo_root/scripts/precheck_tenant_import_rehearsal_env_file.sh"
printer_script="$repo_root/scripts/print_tenant_import_rehearsal_commands.sh"

mkdir -p "$(dirname "$output_path")"

if [[ -n "$env_file" ]]; then
  "$env_precheck_script" \
    --env-file "$env_file" \
    --source-url-env "$source_url_env" \
    --target-url-env "$target_url_env"
  set -a
  # shellcheck disable=SC1090
  . "$env_file"
  set +a
else
  "$env_precheck_script" \
    --source-url-env "$source_url_env" \
    --target-url-env "$target_url_env"
fi

"$precheck_script" \
  --artifact-prefix "$artifact_prefix" \
  --source-url-env "$source_url_env" \
  --target-url-env "$target_url_env"

if [[ -n "$env_file" ]]; then
  "$printer_script" \
    --artifact-prefix "$artifact_prefix" \
    --env-file "$env_file" \
    --source-url-env "$source_url_env" \
    --target-url-env "$target_url_env" \
    > "$output_path"
else
  "$printer_script" \
    --artifact-prefix "$artifact_prefix" \
    --source-url-env "$source_url_env" \
    --target-url-env "$target_url_env" \
    > "$output_path"
fi

echo
echo "Operator command file: $output_path"
echo "Ready for operator command execution: true"
echo "Ready for cutover: false"
