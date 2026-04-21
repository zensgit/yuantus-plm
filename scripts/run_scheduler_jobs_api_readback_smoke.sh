#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_scheduler_jobs_api_readback_smoke.sh [options]

Options:
  --base-url <url>            Running API base URL. default: http://127.0.0.1:7910
  --db-url <url>              SQLite database URL used by that API.
                              default: sqlite:///<repo>/local-dev-env/data/yuantus.db
  --output-dir <path>         Evidence output directory.
                              default: ./tmp/scheduler-jobs-api-readback-<timestamp>
  --tenant <tenant-id>        Tenant id. default: tenant-1
  --org <org-id>              Org id. default: org-1
  --token <jwt>               Existing bearer token. Optional.
  --username <name>           Login username when token is absent. default: admin
  --password <password>       Login password when token is absent. default: admin
  -h, --help                  Show help.

Behavior:
  - local-dev only; refuses DB URLs outside ./local-dev-env/data/
  - runs run_scheduler_audit_retention_activation_smoke.sh to create and complete one job
  - starts a temporary local API if BASE_URL is not already reachable
  - logs into the running API when --token is absent
  - reads back that completed job via GET /api/v1/jobs/{job_id}
  - writes job_readback.json and validation.json

Safety:
  Do not use this script against shared-dev, production, or any DB with data you need.
  The activation smoke is intentionally destructive inside local-dev-env/data only.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

py="${PY:-${repo_root}/.venv/bin/python}"
base_url="${BASE_URL:-http://127.0.0.1:7910}"
db_url="sqlite:///${repo_root}/local-dev-env/data/yuantus.db"
output_dir="${repo_root}/tmp/scheduler-jobs-api-readback-${timestamp}"
tenant_id="tenant-1"
org_id="org-1"
token="${TOKEN:-${AUTH_TOKEN:-}}"
username="${USERNAME:-admin}"
password="${PASSWORD:-admin}"

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "${value}" ]]; then
    echo "Missing value for ${flag}" >&2
    usage >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      require_value "$1" "${2:-}"
      base_url="$2"
      shift 2
      ;;
    --db-url)
      require_value "$1" "${2:-}"
      db_url="$2"
      shift 2
      ;;
    --output-dir)
      require_value "$1" "${2:-}"
      output_dir="$2"
      shift 2
      ;;
    --tenant)
      require_value "$1" "${2:-}"
      tenant_id="$2"
      shift 2
      ;;
    --org)
      require_value "$1" "${2:-}"
      org_id="$2"
      shift 2
      ;;
    --token)
      require_value "$1" "${2:-}"
      token="$2"
      shift 2
      ;;
    --username)
      require_value "$1" "${2:-}"
      username="$2"
      shift 2
      ;;
    --password)
      require_value "$1" "${2:-}"
      password="$2"
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

if [[ ! -x "${py}" ]]; then
  echo "Missing Python at ${py}; set PY=..." >&2
  exit 2
fi

if [[ "${db_url}" != sqlite:///* ]]; then
  echo "Refusing non-sqlite DB URL: ${db_url}" >&2
  echo "This jobs API readback smoke is local-dev only." >&2
  exit 2
fi

db_path="${db_url#sqlite:///}"
case "${db_path}" in
  /*) abs_db_path="${db_path}" ;;
  *) abs_db_path="${repo_root}/${db_path}" ;;
esac

local_data_dir="${repo_root}/local-dev-env/data"
case "${abs_db_path}" in
  "${local_data_dir}"/*) ;;
  *)
    echo "Refusing DB outside local-dev-env/data: ${abs_db_path}" >&2
    echo "Run local-dev-env/start.sh first, then target its sqlite DB." >&2
    exit 2
    ;;
esac

if [[ ! -f "${abs_db_path}" ]]; then
  echo "Missing local dev DB: ${abs_db_path}" >&2
  echo "Run: bash local-dev-env/start.sh" >&2
  exit 2
fi

audit_script="${repo_root}/scripts/run_scheduler_audit_retention_activation_smoke.sh"
if [[ ! -x "${audit_script}" ]]; then
  echo "Missing executable helper: ${audit_script}" >&2
  exit 2
fi

base_url="${base_url%/}"
mkdir -p "${output_dir}"

api_pid=""
cleanup() {
  if [[ -n "${api_pid}" ]]; then
    kill "${api_pid}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

api_ready() {
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "${base_url}/api/v1/eco/approvals/dashboard/summary" 2>/dev/null || true)"
  [[ "${code}" == "200" || "${code}" == "401" ]]
}

start_temp_api() {
  local parsed host port
  parsed="$("${py}" - <<'PY' "${base_url}"
import sys
from urllib.parse import urlparse

parsed = urlparse(sys.argv[1])
host = parsed.hostname or ""
port = parsed.port or (443 if parsed.scheme == "https" else 80)
if host not in {"127.0.0.1", "localhost"}:
    raise SystemExit(f"cannot auto-start non-local API host: {host}")
print(f"{host} {port}")
PY
)"
  read -r host port <<< "${parsed}"

  env \
    "PYTHONPATH=${repo_root}/src" \
    "YUANTUS_DATABASE_URL=sqlite:///${abs_db_path}" \
    "YUANTUS_TENANCY_MODE=disabled" \
    "${py}" -m uvicorn yuantus.api.app:app \
      --host "${host}" \
      --port "${port}" \
      > "${output_dir}/api.log" 2>&1 &
  api_pid="$!"

  for _ in $(seq 1 20); do
    if api_ready; then
      return 0
    fi
    sleep 1
  done

  echo "Temporary API did not become ready. Check ${output_dir}/api.log" >&2
  exit 2
}

echo "== Scheduler jobs API readback smoke =="
echo "BASE_URL=${base_url}"
echo "DB_URL=sqlite:///${abs_db_path}"
echo "OUTPUT_DIR=${output_dir}"
echo "TENANT=${tenant_id}"
echo "ORG=${org_id}"
echo

activation_dir="${output_dir}/activation"
bash "${audit_script}" \
  --db-url "sqlite:///${abs_db_path}" \
  --output-dir "${activation_dir}" \
  --tenant "${tenant_id}" \
  --org "${org_id}"

job_id="$("${py}" - <<'PY' "${activation_dir}/scheduler_tick.json"
import json
import sys
from pathlib import Path

tick = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
enqueued = tick.get("enqueued") or []
if len(enqueued) != 1:
    raise SystemExit(f"expected one enqueued job, got {len(enqueued)}")
print(enqueued[0]["job_id"])
PY
)"

if ! api_ready; then
  echo "API not reachable at ${base_url}; starting temporary local API for readback."
  start_temp_api
fi

if [[ -z "${token}" ]]; then
  login_file="${output_dir}/login.json"
  curl -sS -X POST "${base_url}/api/v1/auth/login" \
    -H "content-type: application/json" \
    -d "{\"tenant_id\":\"${tenant_id}\",\"org_id\":\"${org_id}\",\"username\":\"${username}\",\"password\":\"${password}\"}" \
    > "${login_file}"
  token="$("${py}" - <<'PY' "${login_file}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
token = payload.get("access_token") or ""
if not token:
    raise SystemExit("missing access_token in login response")
print(token)
PY
)"
fi

curl -sS "${base_url}/api/v1/jobs/${job_id}" \
  -H "authorization: Bearer ${token}" \
  -H "x-tenant-id: ${tenant_id}" \
  -H "x-org-id: ${org_id}" \
  > "${output_dir}/job_readback.json"

"${py}" - <<'PY' "${output_dir}" "${job_id}" > "${output_dir}/validation.json"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_job_id = sys.argv[2]
readback = json.loads((output_dir / "job_readback.json").read_text(encoding="utf-8"))
activation = json.loads((output_dir / "activation" / "validation.json").read_text(encoding="utf-8"))

errors = []
if activation.get("ok") is not True:
    errors.append(f"activation smoke failed: {activation.get('errors')}")
if readback.get("id") != expected_job_id:
    errors.append(f"readback id mismatch: {readback.get('id')} != {expected_job_id}")
if readback.get("task_type") != "audit_retention_prune":
    errors.append(f"unexpected task_type: {readback.get('task_type')}")
if readback.get("status") != "completed":
    errors.append(f"expected completed status, got {readback.get('status')}")
if not readback.get("worker_id"):
    errors.append("missing worker_id")
if not readback.get("completed_at"):
    errors.append("missing completed_at")

result = (readback.get("payload") or {}).get("result") or {}
if result.get("ok") is not True:
    errors.append(f"payload.result.ok is not true: {result}")
if result.get("task") != "audit_retention_prune":
    errors.append(f"unexpected payload result task: {result.get('task')}")
if result.get("deleted") != 2:
    errors.append(f"expected payload.result.deleted=2, got {result.get('deleted')}")

payload = {
    "ok": not errors,
    "errors": errors,
    "job_id": expected_job_id,
    "status": readback.get("status"),
    "task_type": readback.get("task_type"),
    "worker_id": readback.get("worker_id"),
}
print(json.dumps(payload, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
PY

cat > "${output_dir}/README.txt" <<EOF
Scheduler jobs API readback smoke

BASE_URL=${base_url}
DB_URL=sqlite:///${abs_db_path}
TENANT=${tenant_id}
ORG=${org_id}
JOB_ID=${job_id}

Evidence:
- activation/scheduler_tick.json
- activation/worker_once.txt
- activation/validation.json
- job_readback.json
- validation.json

Safety:
- local-dev only
- not for shared-dev or production
- activation step is destructive inside local-dev-env/data only
EOF

echo
echo "Done:"
echo "  ${output_dir}/activation/validation.json"
echo "  ${output_dir}/job_readback.json"
echo "  ${output_dir}/validation.json"
