#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_scheduler_audit_retention_activation_smoke.sh [options]

Options:
  --db-url <url>              SQLite database URL.
                              default: sqlite:///<repo>/local-dev-env/data/yuantus.db
  --output-dir <path>         Evidence output directory.
                              default: ./tmp/scheduler-audit-retention-activation-<timestamp>
  --tenant <tenant-id>        Tenant id for scheduler payload. default: tenant-1
  --org <org-id>              Org id for scheduler payload. default: org-1
  --retention-days <days>     Audit retention days. default: 1
  --retention-max-rows <n>    Audit retention max rows. default: 0
  -h, --help                  Show help.

Behavior:
  - local-dev only; refuses DB URLs outside ./local-dev-env/data/
  - clears local audit_logs and meta_conversion_jobs in the target DB
  - seeds 2 old audit rows and 1 new audit row
  - runs `yuantus scheduler --once --force` with only audit_retention_prune enabled
  - runs `yuantus worker --once` to consume the enqueued job
  - writes JSON/TXT evidence into <output-dir>

Safety:
  Do not use this script against shared-dev, production, or any DB with data you need.
  It is intentionally destructive inside local-dev-env/data only.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

py="${PY:-${repo_root}/.venv/bin/python}"
db_url="sqlite:///${repo_root}/local-dev-env/data/yuantus.db"
output_dir="${repo_root}/tmp/scheduler-audit-retention-activation-${timestamp}"
tenant_id="tenant-1"
org_id="org-1"
retention_days="1"
retention_max_rows="0"

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
    --retention-days)
      require_value "$1" "${2:-}"
      retention_days="$2"
      shift 2
      ;;
    --retention-max-rows)
      require_value "$1" "${2:-}"
      retention_max_rows="$2"
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

mkdir -p "${output_dir}"

common_env=(
  "PYTHONPATH=${repo_root}/src"
  "YUANTUS_DATABASE_URL=sqlite:///${abs_db_path}"
  "YUANTUS_TENANCY_MODE=disabled"
  "YUANTUS_AUDIT_RETENTION_DAYS=${retention_days}"
  "YUANTUS_AUDIT_RETENTION_MAX_ROWS=${retention_max_rows}"
  "YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=false"
  "YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=true"
)

echo "== Scheduler audit-retention activation smoke =="
echo "REPO_ROOT=${repo_root}"
echo "DB_URL=sqlite:///${abs_db_path}"
echo "OUTPUT_DIR=${output_dir}"
echo "TENANT=${tenant_id}"
echo "ORG=${org_id}"
echo "RETENTION_DAYS=${retention_days}"
echo "RETENTION_MAX_ROWS=${retention_max_rows}"
echo

env "${common_env[@]}" "${py}" - <<'PY' "${tenant_id}" "${org_id}" > "${output_dir}/audit_seed.json"
import json
import sys
from datetime import datetime, timedelta

from yuantus.database import get_db_session
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.models.audit import AuditLog

tenant_id = sys.argv[1]
org_id = sys.argv[2]

with get_db_session() as session:
    session.query(ConversionJob).delete()
    session.query(AuditLog).delete()
    now = datetime.utcnow()
    rows = [
        AuditLog(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=1,
            method="GET",
            path="/scheduler-smoke/old-a",
            status_code=200,
            duration_ms=1,
            created_at=now - timedelta(days=3),
        ),
        AuditLog(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=1,
            method="POST",
            path="/scheduler-smoke/old-b",
            status_code=200,
            duration_ms=1,
            created_at=now - timedelta(days=2),
        ),
        AuditLog(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=1,
            method="GET",
            path="/scheduler-smoke/new-c",
            status_code=200,
            duration_ms=1,
            created_at=now,
        ),
    ]
    session.add_all(rows)
    session.flush()
    print(json.dumps(
        {
            "audit_rows_seeded": len(rows),
            "old_rows_expected_to_delete": 2,
            "new_rows_expected_to_keep": 1,
            "job_rows_cleared": True,
            "tenant_id": tenant_id,
            "org_id": org_id,
        },
        indent=2,
        sort_keys=True,
    ))
PY

env "${common_env[@]}" "${py}" -m yuantus scheduler \
  --once \
  --force \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  | tee "${output_dir}/scheduler_tick.json"

env "${common_env[@]}" "${py}" -m yuantus worker \
  --worker-id scheduler-audit-retention-smoke \
  --once \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  | tee "${output_dir}/worker_once.txt"

env "${common_env[@]}" "${py}" - <<'PY' > "${output_dir}/post_worker_summary.json"
import json

from yuantus.database import get_db_session
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.models.audit import AuditLog

with get_db_session() as session:
    jobs = session.query(ConversionJob).order_by(ConversionJob.created_at.asc()).all()
    audits = session.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    print(json.dumps(
        {
            "job_count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "task_type": job.task_type,
                    "status": job.status,
                    "worker_id": job.worker_id,
                    "dedupe_key": job.dedupe_key,
                    "payload_result": (job.payload or {}).get("result"),
                }
                for job in jobs
            ],
            "audit_count_after": len(audits),
            "audit_paths_after": [audit.path for audit in audits],
        },
        indent=2,
        sort_keys=True,
        default=str,
    ))
PY

"${py}" - <<'PY' "${output_dir}" > "${output_dir}/validation.json"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
tick = json.loads((output_dir / "scheduler_tick.json").read_text(encoding="utf-8"))
post = json.loads((output_dir / "post_worker_summary.json").read_text(encoding="utf-8"))

enqueued = tick.get("enqueued") or []
disabled = tick.get("disabled") or []
jobs = post.get("jobs") or []

errors = []
if len(enqueued) != 1:
    errors.append(f"expected exactly one enqueued job, got {len(enqueued)}")
else:
    job = enqueued[0]
    if job.get("task_type") != "audit_retention_prune":
        errors.append(f"unexpected enqueued task_type: {job.get('task_type')}")
    if "scheduler:audit_retention_prune:" not in (job.get("dedupe_key") or ""):
        errors.append("missing audit-retention scheduler dedupe key")

if not any(d.get("task_type") == "eco_approval_escalation" and d.get("reason") == "task_disabled" for d in disabled):
    errors.append("expected eco_approval_escalation to be task_disabled")

if len(jobs) != 1:
    errors.append(f"expected exactly one job row, got {len(jobs)}")
else:
    job = jobs[0]
    result = job.get("payload_result") or {}
    if job.get("status") != "completed":
        errors.append(f"expected completed job, got {job.get('status')}")
    if result.get("deleted") != 2:
        errors.append(f"expected deleted=2, got {result.get('deleted')}")

if post.get("audit_count_after") != 1:
    errors.append(f"expected one audit row after prune, got {post.get('audit_count_after')}")
if post.get("audit_paths_after") != ["/scheduler-smoke/new-c"]:
    errors.append(f"unexpected audit_paths_after: {post.get('audit_paths_after')}")

payload = {"ok": not errors, "errors": errors}
print(json.dumps(payload, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
PY

cat > "${output_dir}/README.txt" <<EOF
Scheduler audit-retention activation smoke

DB_URL=sqlite:///${abs_db_path}
TENANT=${tenant_id}
ORG=${org_id}
RETENTION_DAYS=${retention_days}
RETENTION_MAX_ROWS=${retention_max_rows}

Evidence:
- audit_seed.json
- scheduler_tick.json
- worker_once.txt
- post_worker_summary.json
- validation.json
EOF

echo
echo "Done:"
echo "  ${output_dir}/audit_seed.json"
echo "  ${output_dir}/scheduler_tick.json"
echo "  ${output_dir}/worker_once.txt"
echo "  ${output_dir}/post_worker_summary.json"
echo "  ${output_dir}/validation.json"
