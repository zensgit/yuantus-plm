#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_scheduler_bom_to_mbom_activation_smoke.sh [options]

Options:
  --db-url <url>              SQLite database URL.
                              default: sqlite:///<repo>/local-dev-env/data/yuantus.db
  --output-dir <path>         Evidence output directory.
                              default: ./tmp/scheduler-bom-to-mbom-activation-<timestamp>
  --tenant <tenant-id>        Tenant id for scheduler payload. default: tenant-1
  --org <org-id>              Org id for scheduler payload. default: org-1
  --plant <plant-code>        Plant code stamped on the generated MBOM. default: PLANT-SMOKE
  -h, --help                  Show help.

Behavior:
  - local-dev only; refuses DB URLs outside ./local-dev-env/data/
  - clears local BOM→MBOM scheduler smoke data and meta_conversion_jobs in the target DB
  - seeds one released Part root, one released Part child, and one Part BOM relationship
  - runs `yuantus scheduler --once --force` with only bom_to_mbom_sync enabled
  - runs `yuantus worker --once` to consume the enqueued job
  - verifies one ManufacturingBOM and at least two MBOM lines were created
  - writes JSON/TXT evidence into <output-dir>

Safety:
  Do not use this script against shared-dev, production, or any DB with data you need.
  It is intentionally destructive only for scheduler smoke fixtures inside local-dev-env/data.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"

py="${PY:-${repo_root}/.venv/bin/python}"
db_url="sqlite:///${repo_root}/local-dev-env/data/yuantus.db"
output_dir="${repo_root}/tmp/scheduler-bom-to-mbom-activation-${timestamp}"
tenant_id="tenant-1"
org_id="org-1"
plant_code="PLANT-SMOKE"

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
    --plant)
      require_value "$1" "${2:-}"
      plant_code="$2"
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

root_item_id="scheduler-smoke-ebom-root"
child_item_id="scheduler-smoke-ebom-child"
relationship_id="scheduler-smoke-ebom-rel"

common_env=(
  "PYTHONPATH=${repo_root}/src"
  "YUANTUS_DATABASE_URL=sqlite:///${abs_db_path}"
  "YUANTUS_TENANCY_MODE=disabled"
  "YUANTUS_SCHEDULER_SYSTEM_USER_ID=1"
  "YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=false"
  "YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=false"
  "YUANTUS_SCHEDULER_BOM_TO_MBOM_ENABLED=true"
  "YUANTUS_SCHEDULER_BOM_TO_MBOM_SOURCE_ITEM_IDS=${root_item_id}"
  "YUANTUS_SCHEDULER_BOM_TO_MBOM_PLANT_CODE=${plant_code}"
)

echo "== Scheduler BOM to MBOM activation smoke =="
echo "REPO_ROOT=${repo_root}"
echo "DB_URL=sqlite:///${abs_db_path}"
echo "OUTPUT_DIR=${output_dir}"
echo "TENANT=${tenant_id}"
echo "ORG=${org_id}"
echo "ROOT_ITEM_ID=${root_item_id}"
echo "PLANT=${plant_code}"
echo

env "${common_env[@]}" "${py}" - <<'PY' "${tenant_id}" "${org_id}" "${root_item_id}" "${child_item_id}" "${relationship_id}" "${plant_code}" > "${output_dir}/bom_seed.json"
import json
import sys
import uuid
from datetime import datetime

from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.manufacturing.models import MBOMLine, ManufacturingBOM
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.security.rbac.models import RBACUser

tenant_id = sys.argv[1]
org_id = sys.argv[2]
root_item_id = sys.argv[3]
child_item_id = sys.argv[4]
relationship_id = sys.argv[5]
plant_code = sys.argv[6]

def ensure_item_type(session, item_type_id, *, is_relationship=False):
    item_type = session.get(ItemType, item_type_id)
    if not item_type:
        item_type = ItemType(
            id=item_type_id,
            label=item_type_id,
            is_relationship=is_relationship,
            is_versionable=not is_relationship,
            revision_scheme="A-Z",
        )
        session.add(item_type)
        session.flush()
    item_type.is_relationship = is_relationship
    if item_type_id == "Part BOM":
        item_type.source_item_type_id = "Part"
        item_type.related_item_type_id = "Part"
    return item_type

def ensure_admin(session):
    admin = session.get(RBACUser, 1)
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
    return admin

with get_db_session() as session:
    session.query(ConversionJob).delete()

    for mbom in (
        session.query(ManufacturingBOM)
        .filter(ManufacturingBOM.source_item_id == root_item_id)
        .all()
    ):
        session.delete(mbom)
    session.flush()

    session.query(MBOMLine).filter(MBOMLine.item_id.in_([root_item_id, child_item_id])).delete(
        synchronize_session=False
    )
    for item_id in (relationship_id, child_item_id, root_item_id):
        item = session.get(Item, item_id)
        if item is not None:
            session.delete(item)
    session.flush()

    ensure_item_type(session, "Part", is_relationship=False)
    ensure_item_type(session, "Part BOM", is_relationship=True)
    ensure_admin(session)

    now = datetime.utcnow()
    root = Item(
        id=root_item_id,
        item_type_id="Part",
        config_id="scheduler-smoke-root-config",
        generation=1,
        is_current=True,
        state="Released",
        properties={
            "item_number": "SCHED-MBOM-ROOT",
            "name": "Scheduler Smoke EBOM Root",
            "make_buy": "make",
        },
        created_by_id=1,
        owner_id=1,
        created_at=now,
    )
    child = Item(
        id=child_item_id,
        item_type_id="Part",
        config_id="scheduler-smoke-child-config",
        generation=1,
        is_current=True,
        state="Released",
        properties={
            "item_number": "SCHED-MBOM-CHILD",
            "name": "Scheduler Smoke EBOM Child",
            "make_buy": "buy",
        },
        created_by_id=1,
        owner_id=1,
        created_at=now,
    )
    rel = Item(
        id=relationship_id,
        item_type_id="Part BOM",
        config_id="scheduler-smoke-rel-config",
        generation=1,
        is_current=True,
        state="Active",
        source_id=root_item_id,
        related_id=child_item_id,
        properties={
            "quantity": 2,
            "uom": "EA",
            "find_num": "10",
        },
        created_by_id=1,
        owner_id=1,
        created_at=now,
    )
    session.add_all([root, child, rel])
    session.flush()

    print(json.dumps(
        {
            "tenant_id": tenant_id,
            "org_id": org_id,
            "root_item_id": root_item_id,
            "child_item_id": child_item_id,
            "relationship_id": relationship_id,
            "plant_code": plant_code,
            "expected": {
                "created_mboms": 1,
                "min_mbom_lines": 2,
                "worker_task": "bom_to_mbom_sync",
            },
        },
        indent=2,
        sort_keys=True,
    ))
PY

snapshot() {
  local label="$1"
  env "${common_env[@]}" "${py}" - <<'PY' "${label}" "${output_dir}" "${root_item_id}"
import json
import sys
from pathlib import Path

from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.manufacturing.models import MBOMLine, ManufacturingBOM
from yuantus.meta_engine.models.job import ConversionJob

label = sys.argv[1]
output_dir = Path(sys.argv[2])
root_item_id = sys.argv[3]

with get_db_session() as session:
    mboms = (
        session.query(ManufacturingBOM)
        .filter(ManufacturingBOM.source_item_id == root_item_id)
        .order_by(ManufacturingBOM.created_at.asc())
        .all()
    )
    mbom_ids = [mbom.id for mbom in mboms]
    lines = []
    if mbom_ids:
        lines = (
            session.query(MBOMLine)
            .filter(MBOMLine.mbom_id.in_(mbom_ids))
            .order_by(MBOMLine.level.asc(), MBOMLine.sequence.asc())
            .all()
        )
    jobs = session.query(ConversionJob).order_by(ConversionJob.created_at.asc()).all()
    payload = {
        "label": label,
        "mbom_count": len(mboms),
        "mboms": [
            {
                "id": mbom.id,
                "source_item_id": mbom.source_item_id,
                "name": mbom.name,
                "plant_code": mbom.plant_code,
                "state": mbom.state,
            }
            for mbom in mboms
        ],
        "mbom_line_count": len(lines),
        "mbom_lines": [
            {
                "id": line.id,
                "mbom_id": line.mbom_id,
                "parent_line_id": line.parent_line_id,
                "item_id": line.item_id,
                "level": line.level,
                "quantity": float(line.quantity or 0),
                "unit": line.unit,
                "ebom_relationship_id": line.ebom_relationship_id,
                "make_buy": line.make_buy,
            }
            for line in lines
        ],
        "job_count": len(jobs),
    }

(output_dir / f"{label}_summary.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True, default=str),
    encoding="utf-8",
)
print(json.dumps({"label": label, "mbom_count": len(mboms), "mbom_line_count": len(lines)}, indent=2, sort_keys=True))
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
  --worker-id scheduler-bom-to-mbom-smoke \
  --once \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  | tee "${output_dir}/worker_once.txt"

snapshot after > "${output_dir}/after_snapshot.json"

env "${common_env[@]}" "${py}" - <<'PY' "${root_item_id}" > "${output_dir}/post_worker_summary.json"
import json
import sys

from yuantus.meta_engine.bootstrap import import_all_models
import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.manufacturing.models import MBOMLine, ManufacturingBOM
from yuantus.meta_engine.models.job import ConversionJob

root_item_id = sys.argv[1]

with get_db_session() as session:
    jobs = session.query(ConversionJob).order_by(ConversionJob.created_at.asc()).all()
    mboms = (
        session.query(ManufacturingBOM)
        .filter(ManufacturingBOM.source_item_id == root_item_id)
        .order_by(ManufacturingBOM.created_at.asc())
        .all()
    )
    mbom_ids = [mbom.id for mbom in mboms]
    lines = []
    if mbom_ids:
        lines = (
            session.query(MBOMLine)
            .filter(MBOMLine.mbom_id.in_(mbom_ids))
            .order_by(MBOMLine.level.asc(), MBOMLine.sequence.asc())
            .all()
        )
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
            "mbom_count": len(mboms),
            "mboms": [
                {
                    "id": mbom.id,
                    "source_item_id": mbom.source_item_id,
                    "name": mbom.name,
                    "plant_code": mbom.plant_code,
                    "state": mbom.state,
                }
                for mbom in mboms
            ],
            "mbom_line_count": len(lines),
            "mbom_lines": [
                {
                    "id": line.id,
                    "mbom_id": line.mbom_id,
                    "parent_line_id": line.parent_line_id,
                    "item_id": line.item_id,
                    "level": line.level,
                    "quantity": float(line.quantity or 0),
                    "unit": line.unit,
                    "ebom_relationship_id": line.ebom_relationship_id,
                    "make_buy": line.make_buy,
                }
                for line in lines
            ],
        },
        indent=2,
        sort_keys=True,
        default=str,
    ))
PY

"${py}" - <<'PY' "${output_dir}" "${root_item_id}" "${child_item_id}" "${relationship_id}" "${plant_code}" > "${output_dir}/validation.json"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
root_item_id = sys.argv[2]
child_item_id = sys.argv[3]
relationship_id = sys.argv[4]
plant_code = sys.argv[5]

def load(name):
    return json.loads((output_dir / name).read_text(encoding="utf-8"))

tick = load("scheduler_tick.json")
before = load("before_summary.json")
after = load("after_summary.json")
post = load("post_worker_summary.json")

errors = []
enqueued = tick.get("enqueued") or []
disabled = tick.get("disabled") or []
jobs = post.get("jobs") or []
mboms = post.get("mboms") or []
lines = post.get("mbom_lines") or []

if before.get("mbom_count") != 0:
    errors.append(f"expected no MBOM before run, got {before.get('mbom_count')}")
if before.get("mbom_line_count") != 0:
    errors.append(f"expected no MBOM lines before run, got {before.get('mbom_line_count')}")

if len(enqueued) != 1:
    errors.append(f"expected exactly one enqueued job, got {len(enqueued)}")
else:
    job = enqueued[0]
    if job.get("task_type") != "bom_to_mbom_sync":
        errors.append(f"unexpected enqueued task_type: {job.get('task_type')}")
    if "scheduler:bom_to_mbom_sync:" not in (job.get("dedupe_key") or ""):
        errors.append("missing BOM to MBOM scheduler dedupe key")

for task_type in ("eco_approval_escalation", "audit_retention_prune"):
    if not any(d.get("task_type") == task_type and d.get("reason") == "task_disabled" for d in disabled):
        errors.append(f"expected {task_type} to be task_disabled")

if len(jobs) != 1:
    errors.append(f"expected exactly one job row, got {len(jobs)}")
else:
    job = jobs[0]
    result = job.get("payload_result") or {}
    if job.get("status") != "completed":
        errors.append(f"expected completed job, got {job.get('status')}")
    if result.get("task") != "bom_to_mbom_sync":
        errors.append(f"unexpected worker task result: {result.get('task')}")
    if result.get("created") != 1:
        errors.append(f"expected worker result created=1, got {result.get('created')}")
    if result.get("skipped_count") != 0:
        errors.append(f"expected worker result skipped_count=0, got {result.get('skipped_count')}")
    if result.get("errors"):
        errors.append(f"expected no worker result errors, got {result.get('errors')}")

if after.get("mbom_count") != 1:
    errors.append(f"expected one MBOM after run, got {after.get('mbom_count')}")
if after.get("mbom_line_count") < 2:
    errors.append(f"expected at least two MBOM lines after run, got {after.get('mbom_line_count')}")

if len(mboms) != 1:
    errors.append(f"expected one MBOM row, got {len(mboms)}")
else:
    mbom = mboms[0]
    if mbom.get("source_item_id") != root_item_id:
        errors.append(f"unexpected MBOM source_item_id: {mbom.get('source_item_id')}")
    if mbom.get("plant_code") != plant_code:
        errors.append(f"unexpected MBOM plant_code: {mbom.get('plant_code')}")

line_item_ids = {line.get("item_id") for line in lines}
if root_item_id not in line_item_ids:
    errors.append("missing root item MBOM line")
if child_item_id not in line_item_ids:
    errors.append("missing child item MBOM line")
if not any(line.get("ebom_relationship_id") == relationship_id for line in lines):
    errors.append("missing MBOM line traceability to EBOM relationship")

payload = {"ok": not errors, "errors": errors}
print(json.dumps(payload, indent=2, sort_keys=True))
if errors:
    raise SystemExit(1)
PY

cat > "${output_dir}/README.txt" <<EOF
Scheduler BOM to MBOM activation smoke

DB_URL=sqlite:///${abs_db_path}
TENANT=${tenant_id}
ORG=${org_id}
ROOT_ITEM_ID=${root_item_id}
CHILD_ITEM_ID=${child_item_id}
PLANT=${plant_code}

Expected transition:
- scheduler enqueues exactly one bom_to_mbom_sync job
- eco_approval_escalation and audit_retention_prune are task_disabled
- worker completes the job
- worker result created=1
- one ManufacturingBOM is created for the source Part
- at least two MBOM lines are created
- child MBOM line keeps ebom_relationship_id traceability

Evidence:
- bom_seed.json
- before_summary.json
- scheduler_tick.json
- worker_once.txt
- after_summary.json
- post_worker_summary.json
- validation.json
EOF

echo
echo "Done:"
echo "  ${output_dir}/bom_seed.json"
echo "  ${output_dir}/before_summary.json"
echo "  ${output_dir}/scheduler_tick.json"
echo "  ${output_dir}/worker_once.txt"
echo "  ${output_dir}/after_summary.json"
echo "  ${output_dir}/post_worker_summary.json"
echo "  ${output_dir}/validation.json"
