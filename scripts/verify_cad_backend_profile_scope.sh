#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  BASE_URL=http://localhost:8000 TOKEN=<jwt> scripts/verify_cad_backend_profile_scope.sh
  BASE_URL=http://localhost:8000 LOGIN_USERNAME=<user> PASSWORD=<password> scripts/verify_cad_backend_profile_scope.sh
  scripts/verify_cad_backend_profile_scope.sh --env-file "$HOME/.config/yuantus/p2-shared-dev.env"

Required env:
  BASE_URL              API base URL
  Authentication        Either:
                        - TOKEN=<jwt>
                        - LOGIN_USERNAME=<user> PASSWORD=<password>

Optional env:
  TENANT_ID             x-tenant-id header value
  ORG_ID                x-org-id header value
  LOGIN_USERNAME        Login username when TOKEN is not provided
                        default: admin
  PASSWORD              Login password when TOKEN is not provided
  OUTPUT_DIR            Output directory
                        default: ./tmp/cad-backend-profile-verify-<timestamp>
  RUN_TENANT_SCOPE      1 to also verify tenant-default override flow
                        default: 1
  ENV_FILE              Optional default env file, same behavior as --env-file
  PY                    Python executable
                        default: python3

Behavior:
  1. GET  /api/v1/cad/backend-profile
  2. PUT  /api/v1/cad/backend-profile      scope=org
  3. GET  /api/v1/cad/backend-profile
  4. GET  /api/v1/cad/capabilities
  5. DELETE or restore org override
  6. Optionally repeat a safe tenant-default flow when it is not masked by an org override

Notes:
  - PUT/DELETE require an admin or superuser token.
  - The script restores org scope to the original state before exiting.
  - Tenant-default verification is skipped if an org override is active, because the current
    read surface only exposes the effective profile for the current context.
  - Do not run this verifier concurrently against the same tenant/org scope, because it
    temporarily mutates scoped config as part of the check.
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
  local parser="python3"

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
    "ENV_FILE",
    "LOGIN_USERNAME",
    "ORG_ID",
    "OUTPUT_DIR",
    "PASSWORD",
    "PY",
    "RUN_TENANT_SCOPE",
    "TENANT_ID",
    "TOKEN",
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

env_file_path="${env_file_arg:-${ENV_FILE:-}}"
if [[ -n "${env_file_path}" ]]; then
  load_env_file "${env_file_path}"
fi

require_env BASE_URL

while [[ "${BASE_URL}" == */ ]]; do
  BASE_URL="${BASE_URL%/}"
done

PY="${PY:-python3}"
RUN_TENANT_SCOPE="${RUN_TENANT_SCOPE:-1}"

timestamp="$(date +%Y%m%d-%H%M%S)"
output_dir="${OUTPUT_DIR:-./tmp/cad-backend-profile-verify-${timestamp}}"
mkdir -p "${output_dir}"

ensure_token() {
  if [[ -n "${TOKEN:-}" ]]; then
    return 0
  fi

  if [[ -z "${PASSWORD:-}" ]]; then
    echo "Missing authentication env: provide TOKEN or PASSWORD (with optional LOGIN_USERNAME)" >&2
    usage >&2
    exit 1
  fi

  local login_file="${output_dir}/login.json"
  local login_username="${LOGIN_USERNAME:-admin}"

  LOGIN_USERNAME_VALUE="${login_username}" \
  PASSWORD_VALUE="${PASSWORD}" \
  TENANT_VALUE="${TENANT_ID:-tenant-1}" \
  ORG_VALUE="${ORG_ID:-org-1}" \
    "${PY}" - <<'PY' > "${output_dir}/login_request.json"
import json
import os

payload = {
    "tenant_id": os.environ["TENANT_VALUE"],
    "username": os.environ["LOGIN_USERNAME_VALUE"],
    "password": os.environ["PASSWORD_VALUE"],
}
org_id = os.environ.get("ORG_VALUE", "").strip()
if org_id:
    payload["org_id"] = org_id
print(json.dumps(payload))
PY

  local status
  status="$(
    curl -sS \
      --connect-timeout 10 \
      --max-time 30 \
      -X POST "${BASE_URL}/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -o "${login_file}" \
      -w "%{http_code}" \
      --data @"${output_dir}/login_request.json"
  )"

  if [[ "${status}" != "200" ]]; then
    echo "Login failed with status ${status}. Body: ${login_file}" >&2
    exit 1
  fi

  TOKEN="$("${PY}" - "${login_file}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(payload.get("access_token", ""))
PY
)"

  if [[ -z "${TOKEN}" ]]; then
    echo "Login succeeded but no access_token found in ${login_file}" >&2
    exit 1
  fi
}

ensure_token

auth_header="Authorization: Bearer ${TOKEN}"
tenant_header=()
org_header=()

if [[ -n "${TENANT_ID:-}" ]]; then
  tenant_header=(-H "x-tenant-id: ${TENANT_ID}")
fi

if [[ -n "${ORG_ID:-}" ]]; then
  org_header=(-H "x-org-id: ${ORG_ID}")
fi

request_json() {
  local method="$1"
  local path="$2"
  local outfile="$3"
  local expected_codes="$4"
  local body_file="${5:-}"
  local status
  local curl_args=(
    -sS
    --connect-timeout 10
    --max-time 30
    -X "${method}"
    -H "${auth_header}"
    -H "Accept: application/json"
  )

  if [[ ${#tenant_header[@]} -gt 0 ]]; then
    curl_args+=("${tenant_header[@]}")
  fi
  if [[ ${#org_header[@]} -gt 0 ]]; then
    curl_args+=("${org_header[@]}")
  fi
  if [[ -n "${body_file}" ]]; then
    curl_args+=(-H "Content-Type: application/json" --data @"${body_file}")
  fi

  status="$(
    curl "${curl_args[@]}" \
      -o "${outfile}" \
      -w "%{http_code}" \
      "${BASE_URL}${path}"
  )"

  case ",${expected_codes}," in
    *,"${status}",*)
      printf '[ok] %s %s -> %s (%s)\n' "${method}" "${path}" "${status}" "${outfile}"
      ;;
    *)
      printf '[fail] %s %s -> %s expected one of %s\n' "${method}" "${path}" "${status}" "${expected_codes}" >&2
      printf 'Body saved to %s\n' "${outfile}" >&2
      exit 1
      ;;
  esac
}

json_get() {
  local file="$1"
  local path="$2"
  "${PY}" - "${file}" "${path}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    value = json.load(handle)

for part in sys.argv[2].split("."):
    if not part:
        continue
    if isinstance(value, dict):
        value = value.get(part)
    else:
        value = None
        break

if value is None:
    print("")
elif isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
PY
}

assert_json_equals() {
  local file="$1"
  local path="$2"
  local expected="$3"
  local actual
  actual="$(json_get "${file}" "${path}")"
  if [[ "${actual}" != "${expected}" ]]; then
    printf 'Assertion failed for %s in %s: expected %s got %s\n' "${path}" "${file}" "${expected}" "${actual}" >&2
    exit 1
  fi
  printf '[ok] assert %s == %s (%s)\n' "${path}" "${expected}" "${file}"
}

write_put_body() {
  local profile="$1"
  local scope="$2"
  local outfile="$3"
  PROFILE_VALUE="${profile}" SCOPE_VALUE="${scope}" "${PY}" - <<'PY' > "${outfile}"
import json
import os

print(json.dumps({
    "profile": os.environ["PROFILE_VALUE"],
    "scope": os.environ["SCOPE_VALUE"],
}))
PY
}

choose_alternate_profile() {
  local current="$1"
  case "${current}" in
    local-baseline)
      printf 'hybrid-auto'
      ;;
    *)
      printf 'local-baseline'
      ;;
  esac
}

verify_scope_flow() {
  local scope="$1"
  local expected_source="$2"
  local prefix="$3"

  local before_file="${output_dir}/${prefix}_before.json"
  local put_body="${output_dir}/${prefix}_put.json"
  local put_file="${output_dir}/${prefix}_after_put.json"
  local caps_file="${output_dir}/${prefix}_capabilities.json"
  local restore_body="${output_dir}/${prefix}_restore_put.json"
  local restore_file="${output_dir}/${prefix}_restore.json"
  local final_file="${output_dir}/${prefix}_after_restore.json"

  request_json "GET" "/api/v1/cad/backend-profile" "${before_file}" "200"

  local initial_configured
  local initial_effective
  local initial_source
  local target_profile
  initial_configured="$(json_get "${before_file}" "configured")"
  initial_effective="$(json_get "${before_file}" "effective")"
  initial_source="$(json_get "${before_file}" "source")"
  target_profile="$(choose_alternate_profile "${initial_effective}")"

  write_put_body "${target_profile}" "${scope}" "${put_body}"
  request_json "PUT" "/api/v1/cad/backend-profile" "${put_file}" "200" "${put_body}"
  assert_json_equals "${put_file}" "configured" "${target_profile}"
  assert_json_equals "${put_file}" "effective" "${target_profile}"
  assert_json_equals "${put_file}" "source" "${expected_source}"

  request_json "GET" "/api/v1/cad/backend-profile" "${put_file}" "200"
  assert_json_equals "${put_file}" "configured" "${target_profile}"
  assert_json_equals "${put_file}" "effective" "${target_profile}"
  assert_json_equals "${put_file}" "source" "${expected_source}"

  request_json "GET" "/api/v1/cad/capabilities" "${caps_file}" "200"
  assert_json_equals "${caps_file}" "integrations.cad_connector.profile.configured" "${target_profile}"
  assert_json_equals "${caps_file}" "integrations.cad_connector.profile.effective" "${target_profile}"
  assert_json_equals "${caps_file}" "integrations.cad_connector.profile.source" "${expected_source}"

  if [[ "${initial_source}" == "${expected_source}" ]]; then
    write_put_body "${initial_configured}" "${scope}" "${restore_body}"
    request_json "PUT" "/api/v1/cad/backend-profile" "${restore_file}" "200" "${restore_body}"
  else
    request_json "DELETE" "/api/v1/cad/backend-profile?scope=${scope}" "${restore_file}" "200"
  fi

  request_json "GET" "/api/v1/cad/backend-profile" "${final_file}" "200"
  assert_json_equals "${final_file}" "effective" "${initial_effective}"
  assert_json_equals "${final_file}" "source" "${initial_source}"

  printf '[ok] %s scope restored to %s (%s)\n' "${scope}" "${initial_effective}" "${initial_source}"
}

echo "== CAD backend profile scope verification =="
echo "BASE_URL=${BASE_URL}"
echo "OUTPUT_DIR=${output_dir}"
echo

verify_scope_flow "org" "plugin-config:tenant-org" "org_scope"

tenant_status="skipped"
tenant_reason="masked by active org override"
tenant_before_file="${output_dir}/tenant_probe_before.json"
request_json "GET" "/api/v1/cad/backend-profile" "${tenant_before_file}" "200"

if [[ "${RUN_TENANT_SCOPE}" == "1" ]]; then
  current_source="$(json_get "${tenant_before_file}" "source")"
  if [[ "${current_source}" != "plugin-config:tenant-org" ]]; then
    verify_scope_flow "tenant" "plugin-config:tenant-default" "tenant_scope"
    tenant_status="ok"
    tenant_reason="tenant-default override verified and restored"
  fi
else
  tenant_reason="RUN_TENANT_SCOPE=0"
fi

cat > "${output_dir}/README.txt" <<EOF
CAD Backend Profile Scope Verification
Timestamp: ${timestamp}
Base URL: ${BASE_URL}
Tenant ID: ${TENANT_ID:-}
Org ID: ${ORG_ID:-}

Flows:
  org_scope: ok
  tenant_scope: ${tenant_status}
  tenant_scope_reason: ${tenant_reason}

Artifacts:
  org_scope_before.json
  org_scope_after_put.json
  org_scope_capabilities.json
  org_scope_restore.json
  org_scope_after_restore.json
  tenant_probe_before.json
EOF

if [[ "${tenant_status}" == "ok" ]]; then
  cat >> "${output_dir}/README.txt" <<'EOF'
  tenant_scope_before.json
  tenant_scope_after_put.json
  tenant_scope_capabilities.json
  tenant_scope_restore.json
  tenant_scope_after_restore.json
EOF
fi

echo
echo "ALL CHECKS PASSED"
echo "README: ${output_dir}/README.txt"
