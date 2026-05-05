#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/precheck_tenant_import_rehearsal_env_file.sh [--env-file PATH] [--source-url-env NAME] [--target-url-env NAME]

Options:
  --env-file PATH       Optional env-file to load before validation.
  --source-url-env NAME Source database URL variable name.
                        Default: SOURCE_DATABASE_URL
  --target-url-env NAME Target database URL variable name.
                        Default: TARGET_DATABASE_URL
  -h, --help            Show this help.

Validate the P3.4 tenant import rehearsal source/target database URL variables
before a real row-copy command runs. When --env-file is provided, the file must
contain only comments, blank lines, or static KEY=VALUE assignments before it
is loaded. This precheck does not connect to any database, does not run row-copy,
and does not print database URL values.
USAGE
}

env_file=""
source_url_env="SOURCE_DATABASE_URL"
target_url_env="TARGET_DATABASE_URL"

while [[ $# -gt 0 ]]; do
  case "$1" in
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

validate_env_file_static_safety() {
  local file="$1"
  local line_number=0
  local line=""
  local inner=""
  local value=""

  while IFS= read -r line || [[ -n "$line" ]]; do
    line_number=$((line_number + 1))

    if [[ "$line" =~ ^[[:space:]]*$ || "$line" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    if [[ "$line" == *'$('* || "$line" == *'`'* || "$line" == *'${'* || "$line" == *'$['* ]]; then
      echo "error: env-file line $line_number contains shell expansion syntax" >&2
      return 2
    fi

    if [[ ! "$line" =~ ^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=(.*)$ ]]; then
      echo "error: env-file line $line_number must be a static KEY=VALUE assignment" >&2
      return 2
    fi

    value="${BASH_REMATCH[2]}"
    case "$value" in
      "'"*"'")
        inner="${value:1:$(( ${#value} - 2 ))}"
        if [[ "$inner" == *"'"* ]]; then
          echo "error: env-file line $line_number has unsupported quoted value syntax" >&2
          return 2
        fi
        ;;
      *'"'*)
        echo "error: env-file line $line_number must use single quotes for values that require quoting" >&2
        return 2
        ;;
      *)
        if [[ ! "$value" =~ ^[A-Za-z0-9_./:@%+=,-]+$ ]]; then
          echo "error: env-file line $line_number has unsupported value syntax; use single quotes" >&2
          return 2
        fi
        ;;
    esac
  done < "$file"
}

if [[ -n "$env_file" ]]; then
  if [[ ! -f "$env_file" ]]; then
    echo "error: --env-file does not exist: $env_file" >&2
    exit 2
  fi
  validate_env_file_static_safety "$env_file"
  set -a
  # shellcheck disable=SC1090
  . "$env_file"
  set +a
fi

validate_url_var() {
  local name="$1"
  local value="${!name:-}"

  if [[ -z "$value" ]]; then
    echo "error: $name is not set" >&2
    return 2
  fi

  if [[ "$value" == *"REPLACE_ME"* || "$value" == *"change-me"* || "$value" == *"<"* || "$value" == *">"* ]]; then
    echo "error: $name still contains a placeholder value" >&2
    return 2
  fi

  if [[ "$value" != postgresql://* && "$value" != postgresql+*://* ]]; then
    echo "error: $name must be a PostgreSQL database URL" >&2
    return 2
  fi

  return 0
}

validate_url_var "$source_url_env"
validate_url_var "$target_url_env"

cat <<EOF
P3.4 tenant import rehearsal env precheck passed.

Source variable: $source_url_env
Target variable: $target_url_env
Database URL values hidden: true
Ready for row-copy command: true
Ready for cutover: false
EOF
