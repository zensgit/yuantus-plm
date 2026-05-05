#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/precheck_tenant_import_rehearsal_operator.sh \
    --artifact-prefix PREFIX \
    [--source-url-env NAME] \
    [--target-url-env NAME]

Run a DB-free precheck before the operator executes the P3.4 tenant import
rehearsal command sequence.

The precheck validates:

  - implementation packet exists;
  - implementation packet is green;
  - implementation packet keeps ready_for_cutover=false;
  - source/target DSN environment variables are set;
  - required repo-local helper scripts exist and are executable.

It does not print secret DSN values, open database connections, execute
row-copy, accept evidence, build archives, or authorize cutover.
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

validate_env_var_name() {
  local option="$1"
  local name="$2"

  if [[ ! "$name" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
    echo "error: $option must be an uppercase shell environment variable name ([A-Z_][A-Z0-9_]*)" >&2
    return 2
  fi
}

if [[ -z "$artifact_prefix" ]]; then
  echo "error: --artifact-prefix is required" >&2
  usage >&2
  exit 2
fi

validate_env_var_name "--source-url-env" "$source_url_env"
validate_env_var_name "--target-url-env" "$target_url_env"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
implementation_packet_json="${artifact_prefix}_importer_implementation_packet.json"
failures=()

if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
else
  python_bin="python"
fi

check_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    failures+=("missing file: $path")
  fi
}

check_executable() {
  local path="$1"
  if [[ ! -x "$path" ]]; then
    failures+=("missing executable: $path")
  fi
}

check_env_set() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    failures+=("missing environment variable: $name")
  fi
}

check_file "$implementation_packet_json"
check_executable "$repo_root/scripts/print_tenant_import_rehearsal_commands.sh"
check_executable "$repo_root/scripts/run_tenant_import_operator_launchpack.sh"
check_executable "$repo_root/scripts/run_tenant_import_evidence_closeout.sh"
check_env_set "$source_url_env"
check_env_set "$target_url_env"

if [[ -f "$implementation_packet_json" ]]; then
  packet_check="$(
    "$python_bin" - "$implementation_packet_json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text())
except Exception as exc:
    print(f"implementation packet is not valid JSON: {exc}")
    raise SystemExit(0)

expected_schema = "p3.4.2-importer-implementation-packet-v1"
issues = []
if payload.get("schema_version") != expected_schema:
    issues.append(f"implementation packet schema_version must be {expected_schema}")
if payload.get("ready_for_claude_importer") is not True:
    issues.append("implementation packet must have ready_for_claude_importer=true")
if payload.get("ready_for_cutover") is not False:
    issues.append("implementation packet must have ready_for_cutover=false")
if payload.get("blockers"):
    issues.append("implementation packet must have no blockers")
for issue in issues:
    print(issue)
PY
  )"
  if [[ -n "$packet_check" ]]; then
    while IFS= read -r line; do
      failures+=("$line")
    done <<< "$packet_check"
  fi
fi

echo "P3.4 tenant import rehearsal operator precheck"
echo
echo "Artifact prefix: $artifact_prefix"
echo "Implementation packet: $implementation_packet_json"
echo "Source DSN env: $source_url_env (value hidden)"
echo "Target DSN env: $target_url_env (value hidden)"
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
