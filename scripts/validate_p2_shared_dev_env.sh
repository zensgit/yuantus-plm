#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/validate_p2_shared_dev_env.sh [options]

Options:
  --bootstrap-env <path>    Validate the server-side bootstrap env file
                            default: $HOME/.config/yuantus/bootstrap/shared-dev.bootstrap.env
  --observation-env <path>  Validate the operator-side observation env file
                            default: $HOME/.config/yuantus/p2-shared-dev.env
  --mode <mode>             bootstrap | observation | both
                            default: both
  -h, --help                Show this help

Behavior:
  - parses env files with the same quoted-value rules used by the observation wrappers
  - rejects common placeholders such as <jwt>, <dev-host>, change-me-*
  - requires tenant/org ids for shared-dev execution
  - requires either TOKEN or USERNAME/PASSWORD for the observation env

Notes:
  - run from the repo root because the printed follow-up commands are repo-relative
  - this script validates file contents only; it does not contact the shared-dev server
EOF
}

bootstrap_env="${HOME}/.config/yuantus/bootstrap/shared-dev.bootstrap.env"
observation_env="${HOME}/.config/yuantus/p2-shared-dev.env"
mode="both"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bootstrap-env)
      bootstrap_env="$2"
      shift 2
      ;;
    --observation-env)
      observation_env="$2"
      shift 2
      ;;
    --mode)
      mode="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "${mode}" in
  bootstrap|observation|both)
    ;;
  *)
    echo "Unsupported --mode: ${mode}" >&2
    usage >&2
    exit 1
    ;;
esac

parse_env_file() {
  local env_file="$1"
  local allowlist="$2"

  if [[ ! -f "${env_file}" ]]; then
    echo "Missing env file: ${env_file}" >&2
    exit 1
  fi

  python3 - "${env_file}" "${allowlist}" <<'PY'
import json
import re
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1])
allowed = set(sys.argv[2].split(","))
payload = {}
for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        continue
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        raise SystemExit(f"{path}:{lineno}: expected KEY=VALUE")
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
        raise SystemExit(f"{path}:{lineno}: invalid env key '{key}'")
    if key not in allowed:
        raise SystemExit(f"{path}:{lineno}: unsupported env key '{key}'")
    if value and value[0] in "\"'":
        parsed = shlex.split(value, posix=True)
        if len(parsed) != 1:
            raise SystemExit(f"{path}:{lineno}: quoted value must resolve to one token")
        value = parsed[0]
    payload[key] = value
print(json.dumps(payload, ensure_ascii=True))
PY
}

placeholder_like() {
  local value="$1"
  [[ -z "${value}" ]] && return 0
  [[ "${value}" == *"<"*">"* ]] && return 0
  [[ "${value}" == change-me* ]] && return 0
  return 1
}

validate_nonempty() {
  local name="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    echo "Missing required value: ${name}" >&2
    exit 1
  fi
}

validate_not_placeholder() {
  local name="$1"
  local value="$2"
  validate_nonempty "${name}" "${value}"
  if placeholder_like "${value}"; then
    echo "Refusing placeholder value for ${name}: ${value}" >&2
    exit 1
  fi
}

bootstrap_json=""
observation_json=""

if [[ "${mode}" == "bootstrap" || "${mode}" == "both" ]]; then
  bootstrap_json="$(
    parse_env_file \
      "${bootstrap_env}" \
      "YUANTUS_BOOTSTRAP_ADMIN_PASSWORD,YUANTUS_BOOTSTRAP_ADMIN_ROLES,YUANTUS_BOOTSTRAP_ADMIN_USER_ID,YUANTUS_BOOTSTRAP_ADMIN_USERNAME,YUANTUS_BOOTSTRAP_DATASET_MODE,YUANTUS_BOOTSTRAP_FIXTURE_MANIFEST_PATH,YUANTUS_BOOTSTRAP_ORG_ID,YUANTUS_BOOTSTRAP_SKIP_META,YUANTUS_BOOTSTRAP_TENANT_ID,YUANTUS_BOOTSTRAP_VIEWER_PASSWORD,YUANTUS_BOOTSTRAP_VIEWER_ROLES,YUANTUS_BOOTSTRAP_VIEWER_USER_ID,YUANTUS_BOOTSTRAP_VIEWER_USERNAME"
  )"

  eval "$(
    BOOTSTRAP_JSON="${bootstrap_json}" python3 - <<'PY'
import json
import os
payload = json.loads(os.environ["BOOTSTRAP_JSON"])
for key, value in payload.items():
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    print(f'{key}="{escaped}"')
PY
  )"

  validate_not_placeholder "YUANTUS_BOOTSTRAP_TENANT_ID" "${YUANTUS_BOOTSTRAP_TENANT_ID:-}"
  validate_not_placeholder "YUANTUS_BOOTSTRAP_ORG_ID" "${YUANTUS_BOOTSTRAP_ORG_ID:-}"
  validate_not_placeholder "YUANTUS_BOOTSTRAP_ADMIN_USERNAME" "${YUANTUS_BOOTSTRAP_ADMIN_USERNAME:-}"
  validate_not_placeholder "YUANTUS_BOOTSTRAP_ADMIN_PASSWORD" "${YUANTUS_BOOTSTRAP_ADMIN_PASSWORD:-}"
  validate_not_placeholder "YUANTUS_BOOTSTRAP_VIEWER_USERNAME" "${YUANTUS_BOOTSTRAP_VIEWER_USERNAME:-}"
  validate_not_placeholder "YUANTUS_BOOTSTRAP_VIEWER_PASSWORD" "${YUANTUS_BOOTSTRAP_VIEWER_PASSWORD:-}"

  case "${YUANTUS_BOOTSTRAP_DATASET_MODE:-p2-observation}" in
    none|generic|p2-observation)
      ;;
    *)
      echo "Unsupported YUANTUS_BOOTSTRAP_DATASET_MODE: ${YUANTUS_BOOTSTRAP_DATASET_MODE}" >&2
      exit 1
      ;;
  esac

  echo "[ok] bootstrap env: ${bootstrap_env}"
  echo "     tenant/org: ${YUANTUS_BOOTSTRAP_TENANT_ID} / ${YUANTUS_BOOTSTRAP_ORG_ID}"
  echo "     accounts: ${YUANTUS_BOOTSTRAP_ADMIN_USERNAME}, ${YUANTUS_BOOTSTRAP_VIEWER_USERNAME}"
  echo "     dataset: ${YUANTUS_BOOTSTRAP_DATASET_MODE:-p2-observation}"
fi

if [[ "${mode}" == "observation" || "${mode}" == "both" ]]; then
  observation_json="$(
    parse_env_file \
      "${observation_env}" \
      "ARCHIVE_PATH,ARCHIVE_RESULT,BASELINE_DIR,BASELINE_LABEL,BASE_URL,COMPANY_ID,CURRENT_LABEL,DEADLINE_FROM,DEADLINE_TO,ECO_STATE,ECO_TYPE,ENVIRONMENT,EVAL_MODE,EVAL_OUTPUT,EXPECT_DELTAS,OPERATOR,ORG_ID,OUTPUT_DIR,PASSWORD,PY,RUN_WRITE_SMOKE,TENANT_ID,TOKEN,USERNAME"
  )"

  eval "$(
    OBSERVATION_JSON="${observation_json}" python3 - <<'PY'
import json
import os
payload = json.loads(os.environ["OBSERVATION_JSON"])
for key, value in payload.items():
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    print(f'{key}="{escaped}"')
PY
  )"

  validate_not_placeholder "BASE_URL" "${BASE_URL:-}"
  validate_not_placeholder "TENANT_ID" "${TENANT_ID:-}"
  validate_not_placeholder "ORG_ID" "${ORG_ID:-}"
  validate_not_placeholder "ENVIRONMENT" "${ENVIRONMENT:-}"

  if [[ -n "${TOKEN:-}" ]]; then
    validate_not_placeholder "TOKEN" "${TOKEN}"
    auth_mode="token"
  else
    validate_not_placeholder "USERNAME" "${USERNAME:-}"
    validate_not_placeholder "PASSWORD" "${PASSWORD:-}"
    auth_mode="username-password"
  fi

  echo "[ok] observation env: ${observation_env}"
  echo "     base_url: ${BASE_URL}"
  echo "     tenant/org: ${TENANT_ID} / ${ORG_ID}"
  echo "     auth_mode: ${auth_mode}"
fi
