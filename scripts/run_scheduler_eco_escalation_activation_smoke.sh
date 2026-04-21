#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_scheduler_eco_escalation_activation_smoke.sh [options]

Options:
  --db-url <url>              SQLite database URL.
                              default: sqlite:///<repo>/local-dev-env/data/yuantus.db
  --output-dir <path>         Evidence output directory.
                              default: ./tmp/scheduler-eco-escalation-activation-<timestamp>
  --tenant <tenant-id>        Tenant id for scheduler payload. default: tenant-1
  --org <org-id>              Org id for scheduler payload. default: org-1
  -h, --help                  Show help.

Behavior:
  - local-dev only; refuses DB URLs outside ./local-dev-env/data/
  - clears local ECO scheduler smoke data and meta_conversion_jobs in the target DB
  - seeds 1 future pending ECO and 2 overdue ECOs
  - runs `yuantus scheduler --once --force` with only eco_approval_escalation enabled
  - runs `yuantus worker --once` to consume the enqueued job
  - writes before/after dashboard and anomaly evidence into <output-dir>

Safety:
  Do not use this script against shared-dev, production, or any DB with data you need.
  It is intentionally destructive inside local-dev-env/data only.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

py="${PY:-${repo_root}/.venv/bin/python}"
db_url="sqlite:///${repo_root}/local-dev-env/data/yuantus.db"
output_dir="${repo_root}/tmp/scheduler-eco-escalation-activation-${timestamp}"
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
  "YUANTUS_SCHEDULER_SYSTEM_USER_ID=1"
  "YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=true"
  "YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=false"
)

echo "== Scheduler ECO escalation activation smoke =="
echo "REPO_ROOT=${repo_root}"
echo "DB_URL=sqlite:///${abs_db_path}"
echo "OUTPUT_DIR=${output_dir}"
echo "TENANT=${tenant_id}"
echo "ORG=${org_id}"
echo

env "${common_env[@]}" "${py}" - <<'PY' "${tenant_id}" "${org_id}" > "${output_dir}/eco_seed.json"
import json
import sys
import uuid
from datetime import datetime, timedelta

from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.approvals.models import ApprovalRequest, ApprovalRequestEvent
from yuantus.meta_engine.models.eco import ECO, ECOApproval, ECOStage, ECOState
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.security.rbac.models import RBACRole, RBACUser

tenant_id = sys.argv[1]
org_id = sys.argv[2]

def ensure_role(session, name, display_name):
    role = session.query(RBACRole).filter(RBACRole.name == name).first()
    if not role:
        role = RBACRole(name=name, display_name=display_name, is_active=True)
        session.add(role)
        session.flush()
    role.is_active = True
    return role

def ensure_admin(session, engineer_role):
    admin = session.query(RBACUser).filter(RBACUser.id == 1).first()
    if not admin:
        admin = RBACUser(
            id=1,
            user_id=1,
            username="admin",
            email="admin@example.com",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        session.flush()
    admin.is_active = True
    admin.is_superuser = True
    if engineer_role not in (admin.roles or []):
        admin.roles.append(engineer_role)
    return admin

def ensure_ops_user(session):
    ops = session.query(RBACUser).filter(RBACUser.username == "scheduler-smoke-ops").first()
    if not ops:
        ops = RBACUser(
            user_id=920001,
            username="scheduler-smoke-ops",
            email="scheduler-smoke-ops@example.com",
            is_active=True,
            is_superuser=False,
        )
        session.add(ops)
        session.flush()
    ops.is_active = True
    ops.is_superuser = False
    return ops

with get_db_session() as session:
    session.query(ConversionJob).delete()
    session.query(ApprovalRequestEvent).delete()
    session.query(ApprovalRequest).delete()
    session.query(ECOApproval).delete()
    session.query(ECO).delete()
    session.flush()

    engineer = ensure_role(session, "engineer", "Engineer")
    admin = ensure_admin(session, engineer)
    ops = ensure_ops_user(session)

    stage = session.query(ECOStage).filter(ECOStage.name == "SchedulerSmokeReview").first()
    if not stage:
        stage = ECOStage(
            id=str(uuid.uuid4()),
            name="SchedulerSmokeReview",
            sequence=10,
            approval_type="mandatory",
            approval_roles=["engineer"],
            min_approvals=1,
            sla_hours=24,
            auto_progress=False,
        )
        session.add(stage)
        session.flush()
    stage.approval_type = "mandatory"
    stage.approval_roles = ["engineer"]
    stage.min_approvals = 1
    stage.sla_hours = 24
    stage.auto_progress = False

    now = datetime.utcnow()

    def make_eco(name, deadline):
        eco = ECO(
            id=str(uuid.uuid4()),
            name=name,
            eco_type="bom",
            state=ECOState.PROGRESS.value,
            stage_id=stage.id,
            approval_deadline=deadline,
            created_by_id=admin.id,
        )
        session.add(eco)
        session.flush()
        return eco

    eco_pending = make_eco("scheduler-smoke-pending", now + timedelta(hours=20))
    eco_overdue_admin = make_eco("scheduler-smoke-overdue-admin", now - timedelta(hours=5))
    eco_overdue_ops = make_eco("scheduler-smoke-overdue-ops", now - timedelta(hours=3))

    rows = [
        ECOApproval(
            id=str(uuid.uuid4()),
            eco_id=eco_pending.id,
            stage_id=stage.id,
            user_id=admin.id,
            approval_type="mandatory",
            required_role=None,
            status="pending",
        ),
        ECOApproval(
            id=str(uuid.uuid4()),
            eco_id=eco_overdue_admin.id,
            stage_id=stage.id,
            user_id=admin.id,
            approval_type="mandatory",
            required_role=None,
            status="pending",
        ),
        ECOApproval(
            id=str(uuid.uuid4()),
            eco_id=eco_overdue_ops.id,
            stage_id=stage.id,
            user_id=ops.id,
            approval_type="mandatory",
            required_role=None,
            status="pending",
        ),
    ]
    session.add_all(rows)
    session.flush()

    print(json.dumps(
        {
            "tenant_id": tenant_id,
            "org_id": org_id,
            "admin_user_id": admin.id,
            "ops_user_id": ops.id,
            "stage_id": stage.id,
            "ecos": {
                "pending": eco_pending.id,
                "overdue_admin_existing": eco_overdue_admin.id,
                "overdue_ops_escalation_target": eco_overdue_ops.id,
            },
            "expected_before": {
                "pending_count": 1,
                "overdue_count": 2,
                "escalated_count": 0,
                "overdue_not_escalated": 2,
                "escalated_unresolved": 0,
            },
            "expected_after": {
                "pending_count": 1,
                "overdue_count": 3,
                "escalated_count": 1,
                "overdue_not_escalated": 1,
                "escalated_unresolved": 1,
            },
        },
        indent=2,
        sort_keys=True,
    ))
PY

snapshot() {
  local label="$1"
  env "${common_env[@]}" "${py}" - <<'PY' "${label}" "${output_dir}"
import json
import sys
from pathlib import Path

from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.services.eco_service import ECOApprovalService

label = sys.argv[1]
output_dir = Path(sys.argv[2])

with get_db_session() as session:
    svc = ECOApprovalService(session)
    summary = svc.get_approval_dashboard_summary()
    items = svc.get_approval_dashboard_items(limit=100)
    anomalies = svc.get_approval_anomalies()

(output_dir / f"{label}_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True, default=str),
    encoding="utf-8",
)
(output_dir / f"{label}_items.json").write_text(
    json.dumps(items, indent=2, sort_keys=True, default=str),
    encoding="utf-8",
)
(output_dir / f"{label}_anomalies.json").write_text(
    json.dumps(anomalies, indent=2, sort_keys=True, default=str),
    encoding="utf-8",
)
print(json.dumps({"label": label, "items": len(items)}, indent=2, sort_keys=True))
PY
}

snapshot before > "${output_dir}/before_snapshot.json"

env "${common_env[@]}" "${py}" -m yuantus scheduler \
  --once \
  --force \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  | tee "${output_dir}/scheduler_tick.json"

env "${common_env[@]}" "${py}" -m yuantus worker \
  --worker-id scheduler-eco-escalation-smoke \
  --once \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  | tee "${output_dir}/worker_once.txt"

snapshot after > "${output_dir}/after_snapshot.json"

env "${common_env[@]}" "${py}" - <<'PY' > "${output_dir}/post_worker_summary.json"
import json

from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.approvals.models import ApprovalRequest
from yuantus.meta_engine.models.eco import ECOApproval
from yuantus.meta_engine.models.job import ConversionJob

with get_db_session() as session:
    jobs = session.query(ConversionJob).order_by(ConversionJob.created_at.asc()).all()
    approvals = (
        session.query(ECOApproval)
        .order_by(ECOApproval.eco_id.asc(), ECOApproval.created_at.asc())
        .all()
    )
    requests = session.query(ApprovalRequest).order_by(ApprovalRequest.created_at.asc()).all()
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
            "approval_count": len(approvals),
            "admin_escalation_approval_count": len([
                appr for appr in approvals if appr.required_role == "admin"
            ]),
            "approval_request_count": len(requests),
            "approval_requests": [
                {
                    "id": req.id,
                    "entity_type": req.entity_type,
                    "entity_id": req.entity_id,
                    "state": req.state,
                    "priority": req.priority,
                    "assigned_to_id": req.assigned_to_id,
                    "properties": req.properties or {},
                }
                for req in requests
            ],
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

def load(name):
    return json.loads((output_dir / name).read_text(encoding="utf-8"))

tick = load("scheduler_tick.json")
post = load("post_worker_summary.json")
before_summary = load("before_summary.json")
after_summary = load("after_summary.json")
before_anomalies = load("before_anomalies.json")
after_anomalies = load("after_anomalies.json")
before_items = load("before_items.json")
after_items = load("after_items.json")

errors = []
enqueued = tick.get("enqueued") or []
disabled = tick.get("disabled") or []
jobs = post.get("jobs") or []

if len(enqueued) != 1:
    errors.append(f"expected exactly one enqueued job, got {len(enqueued)}")
else:
    job = enqueued[0]
    if job.get("task_type") != "eco_approval_escalation":
        errors.append(f"unexpected enqueued task_type: {job.get('task_type')}")
    if "scheduler:eco_approval_escalation:" not in (job.get("dedupe_key") or ""):
        errors.append("missing ECO escalation scheduler dedupe key")

if not any(d.get("task_type") == "audit_retention_prune" and d.get("reason") == "task_disabled" for d in disabled):
    errors.append("expected audit_retention_prune to be task_disabled")

if len(jobs) != 1:
    errors.append(f"expected exactly one job row, got {len(jobs)}")
else:
    job = jobs[0]
    result = job.get("payload_result") or {}
    if job.get("status") != "completed":
        errors.append(f"expected completed job, got {job.get('status')}")
    if result.get("task") != "eco_approval_escalation":
        errors.append(f"unexpected worker task result: {result.get('task')}")
    if result.get("escalated") != 1:
        errors.append(f"expected worker result escalated=1, got {result.get('escalated')}")

expected_before = {"pending_count": 1, "overdue_count": 2, "escalated_count": 0}
expected_after = {"pending_count": 1, "overdue_count": 3, "escalated_count": 1}
for key, expected in expected_before.items():
    if before_summary.get(key) != expected:
        errors.append(f"before summary {key}: expected {expected}, got {before_summary.get(key)}")
for key, expected in expected_after.items():
    if after_summary.get(key) != expected:
        errors.append(f"after summary {key}: expected {expected}, got {after_summary.get(key)}")

before_overdue_not = len(before_anomalies.get("overdue_not_escalated") or [])
after_overdue_not = len(after_anomalies.get("overdue_not_escalated") or [])
before_unresolved = len(before_anomalies.get("escalated_unresolved") or [])
after_unresolved = len(after_anomalies.get("escalated_unresolved") or [])

if before_overdue_not != 2:
    errors.append(f"expected before overdue_not_escalated=2, got {before_overdue_not}")
if after_overdue_not != 1:
    errors.append(f"expected after overdue_not_escalated=1, got {after_overdue_not}")
if before_unresolved != 0:
    errors.append(f"expected before escalated_unresolved=0, got {before_unresolved}")
if after_unresolved != 1:
    errors.append(f"expected after escalated_unresolved=1, got {after_unresolved}")

if len(before_items) != 3:
    errors.append(f"expected 3 dashboard items before escalation, got {len(before_items)}")
if len(after_items) != 4:
    errors.append(f"expected 4 dashboard items after escalation, got {len(after_items)}")
if post.get("admin_escalation_approval_count") != 1:
    errors.append(
        "expected exactly one admin escalation ECOApproval, "
        f"got {post.get('admin_escalation_approval_count')}"
    )
if post.get("approval_request_count") != 2:
    errors.append(
        "expected two generic ApprovalRequest bridges "
        "(one bridge repair + one new escalation), "
        f"got {post.get('approval_request_count')}"
    )

payload = {"ok": not errors, "errors": errors}
print(json.dumps(payload, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
PY

cat > "${output_dir}/README.txt" <<EOF
Scheduler ECO escalation activation smoke

DB_URL=sqlite:///${abs_db_path}
TENANT=${tenant_id}
ORG=${org_id}

Expected transition:
- summary pending_count stays 1
- summary overdue_count changes 2 -> 3 because escalation creates one admin approval row
- summary escalated_count changes 0 -> 1
- anomalies overdue_not_escalated changes 2 -> 1
- anomalies escalated_unresolved changes 0 -> 1
- generic ApprovalRequest bridges = 2 (existing-admin bridge repair + new admin escalation)

Evidence:
- eco_seed.json
- before_summary.json / before_items.json / before_anomalies.json
- scheduler_tick.json
- worker_once.txt
- after_summary.json / after_items.json / after_anomalies.json
- post_worker_summary.json
- validation.json
EOF

echo
echo "Done:"
echo "  ${output_dir}/eco_seed.json"
echo "  ${output_dir}/before_summary.json"
echo "  ${output_dir}/before_anomalies.json"
echo "  ${output_dir}/scheduler_tick.json"
echo "  ${output_dir}/worker_once.txt"
echo "  ${output_dir}/after_summary.json"
echo "  ${output_dir}/after_anomalies.json"
echo "  ${output_dir}/post_worker_summary.json"
echo "  ${output_dir}/validation.json"
