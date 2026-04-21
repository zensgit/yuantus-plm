#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_scheduler_local_activation_suite.sh [options]

Options:
  --db-url <url>              SQLite database URL.
                              default: sqlite:///<repo>/local-dev-env/data/yuantus.db
  --output-dir <path>         Evidence output directory.
                              default: ./tmp/scheduler-local-activation-suite-<timestamp>
  --tenant <tenant-id>        Tenant id for scheduler payload/context. default: tenant-1
  --org <org-id>              Org id for scheduler payload/context. default: org-1
  -h, --help                  Show help.

Behavior:
  - local-dev only; refuses DB URLs outside ./local-dev-env/data/
  - runs run_scheduler_dry_run_preflight.sh
  - runs run_scheduler_audit_retention_activation_smoke.sh
  - runs run_scheduler_eco_escalation_activation_smoke.sh
  - writes suite_validation.json plus per-step evidence directories

Safety:
  Do not use this script against shared-dev, production, or any DB with data you need.
  The activation smoke steps are intentionally destructive inside local-dev-env/data only.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

py="${PY:-${repo_root}/.venv/bin/python}"
db_url="sqlite:///${repo_root}/local-dev-env/data/yuantus.db"
output_dir="${repo_root}/tmp/scheduler-local-activation-suite-${timestamp}"
tenant_id="tenant-1"
org_id="org-1"

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
  echo "This suite runs activation smokes and is local-dev only." >&2
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

preflight_script="${repo_root}/scripts/run_scheduler_dry_run_preflight.sh"
audit_script="${repo_root}/scripts/run_scheduler_audit_retention_activation_smoke.sh"
eco_script="${repo_root}/scripts/run_scheduler_eco_escalation_activation_smoke.sh"

for script in "${preflight_script}" "${audit_script}" "${eco_script}"; do
  if [[ ! -x "${script}" ]]; then
    echo "Missing executable helper: ${script}" >&2
    exit 2
  fi
done

mkdir -p "${output_dir}"

preflight_dir="${output_dir}/01-dry-run-preflight"
audit_dir="${output_dir}/02-audit-retention-activation"
eco_dir="${output_dir}/03-eco-escalation-activation"

echo "== Scheduler local activation suite =="
echo "REPO_ROOT=${repo_root}"
echo "DB_URL=sqlite:///${abs_db_path}"
echo "OUTPUT_DIR=${output_dir}"
echo "TENANT=${tenant_id}"
echo "ORG=${org_id}"
echo

bash "${preflight_script}" \
  --db-url "sqlite:///${abs_db_path}" \
  --output-dir "${preflight_dir}" \
  --tenant "${tenant_id}" \
  --org "${org_id}"

bash "${audit_script}" \
  --db-url "sqlite:///${abs_db_path}" \
  --output-dir "${audit_dir}" \
  --tenant "${tenant_id}" \
  --org "${org_id}"

bash "${eco_script}" \
  --db-url "sqlite:///${abs_db_path}" \
  --output-dir "${eco_dir}" \
  --tenant "${tenant_id}" \
  --org "${org_id}"

"${py}" - <<'PY' "${output_dir}" > "${output_dir}/suite_validation.json"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
steps = {
    "dry_run_preflight": output_dir / "01-dry-run-preflight" / "validation.json",
    "audit_retention_activation": output_dir / "02-audit-retention-activation" / "validation.json",
    "eco_escalation_activation": output_dir / "03-eco-escalation-activation" / "validation.json",
}

errors = []
loaded = {}
for name, path in steps.items():
    if not path.is_file():
        errors.append(f"missing validation file for {name}: {path}")
        loaded[name] = {"ok": False, "errors": ["missing validation file"]}
        continue
    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded[name] = payload
    if payload.get("ok") is not True:
        errors.append(f"{name} failed validation: {payload.get('errors')}")

suite = {
    "ok": not errors,
    "errors": errors,
    "steps": loaded,
}
print(json.dumps(suite, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
PY

cat > "${output_dir}/README.txt" <<EOF
Scheduler local activation suite

DB_URL=sqlite:///${abs_db_path}
TENANT=${tenant_id}
ORG=${org_id}

Steps:
1. 01-dry-run-preflight
   - validates scheduler dry-run reports would_enqueue without changing meta_conversion_jobs
2. 02-audit-retention-activation
   - validates audit_retention_prune enqueue -> worker completion -> audit rows pruned
3. 03-eco-escalation-activation
   - validates eco_approval_escalation enqueue -> worker completion -> dashboard/anomaly reconciliation

Suite validation:
- suite_validation.json

Safety:
- local-dev only
- not for shared-dev or production
- activation steps are destructive inside local-dev-env/data only
EOF

echo
echo "Done:"
echo "  ${output_dir}/01-dry-run-preflight/validation.json"
echo "  ${output_dir}/02-audit-retention-activation/validation.json"
echo "  ${output_dir}/03-eco-escalation-activation/validation.json"
echo "  ${output_dir}/suite_validation.json"
