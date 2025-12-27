#!/usr/bin/env bash
# =============================================================================
# CAD Extract Local Verification Script
# Verifies cad_extract task without running API server (local storage + sqlite).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_PY="$REPO_ROOT/.venv/bin/python"
if [[ -x "$DEFAULT_PY" ]]; then
  PY="${PY:-$DEFAULT_PY}"
else
  PY="${PY:-python3}"
fi
PYTHONPATH="${PYTHONPATH:-$REPO_ROOT/src}"
export PYTHONPATH

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Missing python at $PY (set PY=...)" >&2
  exit 2
fi

DB_PATH="/tmp/yuantus_cad_extract_local.db"
STORAGE_PATH="/tmp/yuantus_cad_extract_storage"

rm -f "$DB_PATH"
rm -rf "$STORAGE_PATH"

echo "=============================================="
echo "CAD Extract Local Verification"
echo "DB: $DB_PATH"
echo "Storage: $STORAGE_PATH"
echo "=============================================="

YUANTUS_DATABASE_URL="sqlite:///$DB_PATH" \
YUANTUS_SCHEMA_MODE="create_all" \
YUANTUS_TENANCY_MODE="single" \
YUANTUS_LOCAL_STORAGE_PATH="$STORAGE_PATH" \
"$PY" - <<'PY'
import io
import uuid
import hashlib
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.database import init_db, get_db_session
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract
from yuantus.meta_engine.services.file_service import FileService

import_all_models()
init_db(create_tables=True)

content = """图号=HC-LOCAL-001
名称=本地提取测试
版本=A
材料=钢
重量=1.2kg
""".encode("utf-8")
checksum = hashlib.sha256(content).hexdigest()
file_id = str(uuid.uuid4())
storage_key = f"2d/{file_id[:2]}/{file_id}.dwg"
file_service = FileService()
file_service.upload_file(io.BytesIO(content), storage_key)

with get_db_session() as session:
    file_container = FileContainer(
        id=file_id,
        filename="local_extract.dwg",
        file_type="dwg",
        mime_type="application/acad",
        file_size=len(content),
        checksum=checksum,
        system_path=storage_key,
        document_type="2d",
        is_native_cad=True,
        cad_format="GSTARCAD",
        cad_connector_id="gstarcad",
    )
    session.add(file_container)
    session.commit()

    result = cad_extract({"file_id": file_id}, session)
    if not result.get("ok"):
        raise SystemExit("cad_extract failed")

    session.refresh(file_container)
    attrs = file_container.cad_attributes or {}
    if attrs.get("part_number") != "HC-LOCAL-001":
        raise SystemExit(f"part_number mismatch: {attrs.get('part_number')}")
    if attrs.get("description") != "本地提取测试":
        raise SystemExit(f"description mismatch: {attrs.get('description')}")
    weight = attrs.get("weight")
    if weight is None or abs(float(weight) - 1.2) > 1e-6:
        raise SystemExit(f"weight mismatch: {weight}")
    if file_container.cad_attributes_source not in ("local", "external"):
        raise SystemExit(f"source mismatch: {file_container.cad_attributes_source}")

print("ALL CHECKS PASSED")
PY

echo "=============================================="
echo "CAD Extract Local Verification Complete"
echo "=============================================="
