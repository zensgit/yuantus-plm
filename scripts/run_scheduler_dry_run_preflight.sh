#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_scheduler_dry_run_preflight.sh [options]

Options:
  --db-url <url>              Database URL.
                              default: sqlite:///<repo>/local-dev-env/data/yuantus.db
  --output-dir <path>         Evidence output directory.
                              default: ./tmp/scheduler-dry-run-preflight-<timestamp>
  --tenant <tenant-id>        Tenant id for scheduler payload/context. default: tenant-1
  --org <org-id>              Org id for scheduler payload/context. default: org-1
  --tenancy-mode <mode>       YUANTUS_TENANCY_MODE. default: disabled
  --respect-enabled           Do not pass --force; respect YUANTUS_SCHEDULER_ENABLED.
  --allow-non-local-db        Allow non-local-dev DB URLs. Required for shared-dev/prod DBs.
  -h, --help                  Show help.

Behavior:
  - runs `yuantus scheduler --once --dry-run`
  - writes scheduler output plus before/after job counts
  - validates dry-run did not enqueue jobs
  - defaults to local-dev SQLite and refuses non-local DBs unless explicitly allowed

Safety:
  This script is intended as the preflight before any scheduler activation.
  It does not run workers and must not create rows in meta_conversion_jobs.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

py="${PY:-${repo_root}/.venv/bin/python}"
db_url="sqlite:///${repo_root}/local-dev-env/data/yuantus.db"
output_dir="${repo_root}/tmp/scheduler-dry-run-preflight-${timestamp}"
tenant_id="tenant-1"
org_id="org-1"
tenancy_mode="${YUANTUS_TENANCY_MODE:-disabled}"
force_flag="--force"
allow_non_local_db="false"

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
    --tenancy-mode)
      require_value "$1" "${2:-}"
      tenancy_mode="$2"
      shift 2
      ;;
    --respect-enabled)
      force_flag=""
      shift
      ;;
    --allow-non-local-db)
      allow_non_local_db="true"
      shift
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

if [[ "${db_url}" == sqlite:///* ]]; then
  db_path="${db_url#sqlite:///}"
  case "${db_path}" in
    /*) abs_db_path="${db_path}" ;;
    *) abs_db_path="${repo_root}/${db_path}" ;;
  esac

  local_data_dir="${repo_root}/local-dev-env/data"
  case "${abs_db_path}" in
    "${local_data_dir}"/*) ;;
    *)
      if [[ "${allow_non_local_db}" != "true" ]]; then
        echo "Refusing SQLite DB outside local-dev-env/data: ${abs_db_path}" >&2
        echo "Pass --allow-non-local-db only for an explicitly approved dry-run preflight." >&2
        exit 2
      fi
      ;;
  esac

  if [[ ! -f "${abs_db_path}" ]]; then
    echo "Missing SQLite DB: ${abs_db_path}" >&2
    echo "For local dev, run: bash local-dev-env/start.sh" >&2
    exit 2
  fi
else
  if [[ "${allow_non_local_db}" != "true" ]]; then
    echo "Refusing non-local DB URL without --allow-non-local-db: ${db_url}" >&2
    echo "Dry-run is non-mutating, but remote/shared DB targets must be explicit." >&2
    exit 2
  fi
fi

mkdir -p "${output_dir}"

common_env=(
  "PYTHONPATH=${repo_root}/src"
  "YUANTUS_DATABASE_URL=${db_url}"
  "YUANTUS_TENANCY_MODE=${tenancy_mode}"
)

echo "== Scheduler dry-run preflight =="
echo "REPO_ROOT=${repo_root}"
echo "DB_URL=${db_url}"
echo "OUTPUT_DIR=${output_dir}"
echo "TENANT=${tenant_id}"
echo "ORG=${org_id}"
echo "TENANCY_MODE=${tenancy_mode}"
echo "FORCE=$([[ -n "${force_flag}" ]] && echo true || echo false)"
echo

count_jobs() {
  env "${common_env[@]}" "${py}" - <<'PY'
from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.models.job import ConversionJob

with get_db_session() as session:
    print(session.query(ConversionJob).count())
PY
}

job_count_before="$(count_jobs)"

scheduler_cmd=(
  env "${common_env[@]}" "${py}" -m yuantus scheduler
  --once
  --dry-run
  --tenant "${tenant_id}"
  --org "${org_id}"
)
if [[ -n "${force_flag}" ]]; then
  scheduler_cmd+=("${force_flag}")
fi

"${scheduler_cmd[@]}" | tee "${output_dir}/scheduler_dry_run.json"

job_count_after="$(count_jobs)"

cat > "${output_dir}/job_counts.json" <<EOF
{
  "job_count_before": ${job_count_before},
  "job_count_after": ${job_count_after}
}
EOF

"${py}" - <<'PY' "${output_dir}" > "${output_dir}/validation.json"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
dry_run = json.loads((output_dir / "scheduler_dry_run.json").read_text(encoding="utf-8"))
counts = json.loads((output_dir / "job_counts.json").read_text(encoding="utf-8"))

errors = []

for key in ("enqueued", "would_enqueue", "skipped", "disabled"):
    if key not in dry_run:
        errors.append(f"missing scheduler output key: {key}")
    elif not isinstance(dry_run[key], list):
        errors.append(f"scheduler output key is not a list: {key}")

if dry_run.get("enqueued"):
    errors.append(f"dry-run unexpectedly enqueued jobs: {dry_run.get('enqueued')}")

for decision in dry_run.get("would_enqueue") or []:
    if decision.get("action") != "would_enqueue":
        errors.append(f"unexpected would_enqueue action: {decision}")
    if decision.get("reason") != "dry_run_due":
        errors.append(f"unexpected would_enqueue reason: {decision}")
    if decision.get("job_id") is not None:
        errors.append(f"dry-run decision unexpectedly has job_id: {decision}")

if counts.get("job_count_before") != counts.get("job_count_after"):
    errors.append(
        "meta_conversion_jobs changed during dry-run: "
        f"{counts.get('job_count_before')} -> {counts.get('job_count_after')}"
    )

payload = {
    "ok": not errors,
    "errors": errors,
    "job_count_before": counts.get("job_count_before"),
    "job_count_after": counts.get("job_count_after"),
    "would_enqueue_count": len(dry_run.get("would_enqueue") or []),
    "skipped_count": len(dry_run.get("skipped") or []),
    "disabled_count": len(dry_run.get("disabled") or []),
}
print(json.dumps(payload, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
PY

cat > "${output_dir}/README.txt" <<EOF
Scheduler dry-run preflight

DB_URL=${db_url}
TENANT=${tenant_id}
ORG=${org_id}
TENANCY_MODE=${tenancy_mode}
FORCE=$([[ -n "${force_flag}" ]] && echo true || echo false)

Evidence:
- scheduler_dry_run.json
- job_counts.json
- validation.json

This run must not create rows in meta_conversion_jobs.
EOF

echo
echo "Done:"
echo "  ${output_dir}/scheduler_dry_run.json"
echo "  ${output_dir}/job_counts.json"
echo "  ${output_dir}/validation.json"
