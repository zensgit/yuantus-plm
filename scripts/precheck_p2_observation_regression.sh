#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  BASE_URL=http://localhost:8000 TOKEN=<jwt> scripts/precheck_p2_observation_regression.sh
  BASE_URL=http://localhost:8000 USERNAME=<user> PASSWORD=<password> scripts/precheck_p2_observation_regression.sh
  scripts/precheck_p2_observation_regression.sh --env-file ./p2-shared-dev.env

Options:
  --env-file <path>      Load unset precheck env vars from a local KEY=VALUE file
                         File values act as defaults; already-exported env wins
  -h, --help             Show this help

Required env:
  BASE_URL              API base URL
  Authentication        Either:
                        - TOKEN=<jwt>
                        - USERNAME=<user> PASSWORD=<password>

Optional env:
  OUTPUT_DIR            Where to store precheck artifacts
                        default: ./tmp/p2-observation-precheck-<timestamp>
  ENV_FILE              Optional default env file, same behavior as --env-file
  TENANT_ID             x-tenant-id header value
  ORG_ID                x-org-id header value
  USERNAME              Login username when TOKEN is not provided
                        default: admin
  PASSWORD              Login password when TOKEN is not provided
  COMPANY_ID            Optional summary filter
  ECO_TYPE              Optional summary filter
  ECO_STATE             Optional summary filter
  DEADLINE_FROM         Optional summary filter
  DEADLINE_TO           Optional summary filter
  ENVIRONMENT           Optional environment label recorded in the precheck artifact
                        default: precheck
  PY                    Python interpreter used for JSON/env helpers
                        default: python3

Behavior:
  1. If ENV_FILE/--env-file is provided, load missing env defaults from it
  2. If TOKEN is absent, log in via /api/v1/auth/login using USERNAME/PASSWORD
  3. Probe GET /api/v1/eco/approvals/dashboard/summary
  4. Write OBSERVATION_PRECHECK.md and observation_precheck.json
  5. Save the summary response body to summary_probe.json
EOF
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: $name" >&2
    usage >&2
    exit 1
  fi
}

load_env_file() {
  local env_file="$1"
  local key=""
  local value=""
  local parser="${PY:-python3}"

  if [[ ! -f "${env_file}" ]]; then
    echo "Missing env file: ${env_file}" >&2
    exit 1
  fi

  while IFS='=' read -r key value; do
    [[ -n "${key}" ]] || continue
    if [[ -z "${!key+x}" ]]; then
      printf -v "${key}" '%s' "${value}"
      export "${key}"
    fi
  done < <(
    "${parser}" - "${env_file}" <<'PY'
import re
import shlex
import sys
from pathlib import Path

allowed = {
    "BASE_URL",
    "COMPANY_ID",
    "DEADLINE_FROM",
    "DEADLINE_TO",
    "ECO_STATE",
    "ECO_TYPE",
    "ENVIRONMENT",
    "ORG_ID",
    "OUTPUT_DIR",
    "PASSWORD",
    "PY",
    "TENANT_ID",
    "TOKEN",
    "USERNAME",
}

path = Path(sys.argv[1])
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
    print(f"{key}={value}")
PY
  )
}

urlencode() {
  local value="$1"
  local encoded=""
  local char=""
  local i=0

  for ((i = 0; i < ${#value}; i++)); do
    char="${value:i:1}"
    case "${char}" in
      [a-zA-Z0-9.~_-])
        encoded+="${char}"
        ;;
      *)
        printf -v char '%%%02X' "'${char}"
        encoded+="${char}"
        ;;
    esac
  done

  printf '%s' "${encoded}"
}

build_query() {
  local query=""
  local parts=()
  local value=""
  local i=0

  value="${COMPANY_ID:-}"
  if [[ -n "${value}" ]]; then
    parts+=("company_id=$(urlencode "${value}")")
  fi

  value="${ECO_TYPE:-}"
  if [[ -n "${value}" ]]; then
    parts+=("eco_type=$(urlencode "${value}")")
  fi

  value="${ECO_STATE:-}"
  if [[ -n "${value}" ]]; then
    parts+=("eco_state=$(urlencode "${value}")")
  fi

  value="${DEADLINE_FROM:-}"
  if [[ -n "${value}" ]]; then
    parts+=("deadline_from=$(urlencode "${value}")")
  fi

  value="${DEADLINE_TO:-}"
  if [[ -n "${value}" ]]; then
    parts+=("deadline_to=$(urlencode "${value}")")
  fi

  if [[ ${#parts[@]} -gt 0 ]]; then
    query="?${parts[0]}"
    for ((i = 1; i < ${#parts[@]}; i++)); do
      query+="&${parts[i]}"
    done
  fi

  printf '%s' "${query}"
}

write_precheck_artifacts() {
  PRECHECK_RESULT="${result}" \
  PRECHECK_REASON="${reason}" \
  PRECHECK_OUTPUT_DIR="${output_dir}" \
  PRECHECK_BASE_URL="${BASE_URL:-}" \
  PRECHECK_ENV_FILE="${env_file_path:-}" \
  PRECHECK_ENVIRONMENT="${environment_name}" \
  PRECHECK_AUTH_MODE="${auth_mode}" \
  PRECHECK_LOGIN_HTTP_STATUS="${login_http_status}" \
  PRECHECK_SUMMARY_HTTP_STATUS="${summary_http_status}" \
  PRECHECK_TENANT_ID="${TENANT_ID:-}" \
  PRECHECK_ORG_ID="${ORG_ID:-}" \
  PRECHECK_SUMMARY_QUERY="${query}" \
  PRECHECK_JSON_PATH="${output_dir}/observation_precheck.json" \
  PRECHECK_MD_PATH="${output_dir}/OBSERVATION_PRECHECK.md" \
  PRECHECK_PROBE_PATH="${summary_probe_path}" \
  "${PY}" - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "result": os.environ["PRECHECK_RESULT"],
    "reason": os.environ["PRECHECK_REASON"],
    "output_dir": os.environ["PRECHECK_OUTPUT_DIR"],
    "base_url": os.environ["PRECHECK_BASE_URL"],
    "env_file": os.environ["PRECHECK_ENV_FILE"] or None,
    "environment": os.environ["PRECHECK_ENVIRONMENT"],
    "auth_mode": os.environ["PRECHECK_AUTH_MODE"],
    "login_http_status": int(os.environ["PRECHECK_LOGIN_HTTP_STATUS"]) if os.environ["PRECHECK_LOGIN_HTTP_STATUS"] else None,
    "summary_http_status": int(os.environ["PRECHECK_SUMMARY_HTTP_STATUS"]) if os.environ["PRECHECK_SUMMARY_HTTP_STATUS"] else None,
    "tenant_id": os.environ["PRECHECK_TENANT_ID"] or None,
    "org_id": os.environ["PRECHECK_ORG_ID"] or None,
    "summary_query": os.environ["PRECHECK_SUMMARY_QUERY"],
    "summary_probe_path": os.environ["PRECHECK_PROBE_PATH"],
}

Path(os.environ["PRECHECK_JSON_PATH"]).write_text(
    json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
    encoding="utf-8",
)

lines = [
    "# P2 Observation Precheck",
    "",
    f"- result: {payload['result']}",
    f"- reason: {payload['reason']}",
    f"- environment: `{payload['environment']}`",
    f"- base_url: `{payload['base_url']}`",
    f"- output_dir: `{payload['output_dir']}`",
    f"- env_file: `{payload['env_file']}`" if payload["env_file"] else "- env_file: _not provided_",
    f"- auth_mode: `{payload['auth_mode']}`",
    f"- login_http_status: `{payload['login_http_status']}`" if payload["login_http_status"] is not None else "- login_http_status: _n/a_",
    f"- summary_http_status: `{payload['summary_http_status']}`" if payload["summary_http_status"] is not None else "- summary_http_status: _n/a_",
    f"- tenant_id: `{payload['tenant_id']}`" if payload["tenant_id"] else "- tenant_id: _not set_",
    f"- org_id: `{payload['org_id']}`" if payload["org_id"] else "- org_id: _not set_",
    f"- summary_query: `{payload['summary_query']}`" if payload["summary_query"] else "- summary_query: _none_",
    f"- summary_probe: `{payload['summary_probe_path']}`",
]
Path(os.environ["PRECHECK_MD_PATH"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

env_file_arg=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --env-file)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "Missing value for --env-file" >&2
        usage >&2
        exit 1
      fi
      env_file_arg="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

result="failure"
reason="precheck not started"
auth_mode="missing"
login_http_status=""
summary_http_status=""
environment_name="${ENVIRONMENT:-precheck}"
PY="${PY:-python3}"
query=""

env_file_path="${env_file_arg:-${ENV_FILE:-}}"
if [[ -n "${env_file_path}" ]]; then
  load_env_file "${env_file_path}"
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${OUTPUT_DIR:-./tmp/p2-observation-precheck-${timestamp}}"
mkdir -p "${output_dir}"
summary_probe_path="${output_dir}/summary_probe.json"

trap 'write_precheck_artifacts' EXIT

if [[ -z "${BASE_URL:-}" ]]; then
  reason="missing BASE_URL"
  exit 1
fi

while [[ "${BASE_URL}" == */ ]]; do
  BASE_URL="${BASE_URL%/}"
done

query="$(build_query)"

token="${TOKEN:-}"
if [[ -n "${token}" ]]; then
  auth_mode="token"
elif [[ -n "${PASSWORD:-}" ]]; then
  auth_mode="password-login"
  username="${USERNAME:-admin}"
  login_body="$(
    TENANT_ID_VALUE="${TENANT_ID:-}" \
    ORG_ID_VALUE="${ORG_ID:-}" \
    USERNAME_VALUE="${username}" \
    PASSWORD_VALUE="${PASSWORD}" \
    "${PY}" - <<'PY'
import json
import os
import sys

payload = {
    "tenant_id": os.environ["TENANT_ID_VALUE"],
    "org_id": os.environ["ORG_ID_VALUE"],
    "username": os.environ["USERNAME_VALUE"],
    "password": os.environ["PASSWORD_VALUE"],
}
json.dump(payload, sys.stdout, ensure_ascii=True, separators=(",", ":"))
PY
  )"

  login_tmp="$(mktemp)"
  trap 'rm -f "${login_tmp}" >/dev/null 2>&1 || true; write_precheck_artifacts' EXIT
  login_http_status="$(
    curl -sS -o "${login_tmp}" -w "%{http_code}" \
      -X POST "${BASE_URL}/api/v1/auth/login" \
      -H 'content-type: application/json' \
      --data-binary "${login_body}"
  )"
  if [[ "${login_http_status}" != "200" ]]; then
    reason="login failed -> HTTP ${login_http_status}"
    exit 1
  fi
  token="$(
    LOGIN_JSON_PATH="${login_tmp}" \
    "${PY}" - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["LOGIN_JSON_PATH"]).read_text(encoding="utf-8"))
access_token = payload.get("access_token")
if not isinstance(access_token, str) or not access_token:
    raise SystemExit("missing access_token in login response")
print(access_token)
PY
  )"
  if [[ -z "${token}" ]]; then
    reason="missing access_token in login response"
    exit 1
  fi
else
  reason="missing authentication env: provide TOKEN or PASSWORD"
  exit 1
fi

auth_header="Authorization: Bearer ${token}"
curl_args=(
  -sS
  --connect-timeout 10
  --max-time 30
  -H "${auth_header}"
  -H "Accept: application/json"
)

if [[ -n "${TENANT_ID:-}" ]]; then
  curl_args+=(-H "x-tenant-id: ${TENANT_ID}")
fi
if [[ -n "${ORG_ID:-}" ]]; then
  curl_args+=(-H "x-org-id: ${ORG_ID}")
fi

summary_http_status="$(
  curl "${curl_args[@]}" \
    -o "${summary_probe_path}" \
    -w "%{http_code}" \
    "${BASE_URL}/api/v1/eco/approvals/dashboard/summary${query}"
)"

if [[ "${summary_http_status}" != "200" ]]; then
  reason="summary probe failed -> HTTP ${summary_http_status}"
  exit 1
fi

result="success"
reason="summary endpoint ok"

echo "== P2 observation precheck =="
echo "BASE_URL=${BASE_URL}"
echo "OUTPUT_DIR=${output_dir}"
if [[ -n "${env_file_path}" ]]; then
  echo "ENV_FILE=${env_file_path}"
fi
echo "AUTH_MODE=${auth_mode}"
echo "SUMMARY_HTTP_STATUS=${summary_http_status}"
echo
echo "Done:"
echo "  ${output_dir}/OBSERVATION_PRECHECK.md"
echo "  ${output_dir}/observation_precheck.json"
echo "  ${summary_probe_path}"
