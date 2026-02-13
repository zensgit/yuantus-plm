#!/usr/bin/env bash
# =============================================================================
# CAD Attribute Normalization Verification Script
# Verifies material/weight/revision normalization and alias key handling.
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

DB_PATH="/tmp/yuantus_cad_attr_norm.db"
STORAGE_PATH="/tmp/yuantus_cad_attr_norm_storage"

rm -f "$DB_PATH"
rm -rf "$STORAGE_PATH"

echo "=============================================="
echo "CAD Attribute Normalization Verification"
echo "DB: $DB_PATH"
echo "Storage: $STORAGE_PATH"
echo "=============================================="

YUANTUS_DATABASE_URL="sqlite:///$DB_PATH" \
YUANTUS_SCHEMA_MODE="create_all" \
YUANTUS_TENANCY_MODE="single" \
YUANTUS_STORAGE_TYPE="local" \
YUANTUS_LOCAL_STORAGE_PATH="$STORAGE_PATH" \
YUANTUS_CAD_EXTRACTOR_BASE_URL="" \
"$PY" - <<'PY'
import io
import uuid
import hashlib

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.database import init_db, get_db_session
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract

import_all_models()
init_db(create_tables=True)

samples = [
    {
        "label": "HAOCHEN",
        "filename": "normalize_sample.dwg",
        "cad_format": "HAOCHEN",
        "connector_id": "haochencad",
        "content": """图号=NORM-001
名称=归一化测试
版本=REV-A
材料=不锈钢304
重量=1200g
""",
        "expected": {
            "part_number": "NORM-001",
            "drawing_no": "NORM-001",
            "material": "Stainless Steel 304",
            "revision": "A",
            "weight": 1.2,
        },
    },
    {
        "label": "ZHONGWANG",
        "filename": "normalize_zw.dwg",
        "cad_format": "ZHONGWANG",
        "connector_id": "zhongwangcad",
        "content": """图纸编号=ZW-002
图纸名称=中望归一化测试
版次=REV-B
材质=Q235
重量(kg)=2.5kg
""",
        "expected": {
            "part_number": "ZW-002",
            "drawing_no": "ZW-002",
            "material": "Q235 Steel",
            "revision": "B",
            "weight": 2.5,
        },
    },
]

file_service = FileService()

with get_db_session() as session:
    for sample in samples:
        raw = sample["content"].encode("utf-8")
        checksum = hashlib.sha256(raw).hexdigest()
        file_id = str(uuid.uuid4())
        storage_key = f"norm/{file_id[:2]}/{file_id}.dwg"
        file_service.upload_file(io.BytesIO(raw), storage_key)

        file_container = FileContainer(
            id=file_id,
            filename=sample["filename"],
            file_type="dwg",
            mime_type="application/acad",
            file_size=len(raw),
            checksum=checksum,
            system_path=storage_key,
            document_type="2d",
            is_native_cad=True,
            cad_format=sample["cad_format"],
            cad_connector_id=sample["connector_id"],
        )
        session.add(file_container)
        session.commit()

        result = cad_extract({"file_id": file_id}, session)
        if not result.get("ok"):
            raise SystemExit(f"cad_extract failed ({sample['label']})")

        session.refresh(file_container)
        attrs = file_container.cad_attributes or {}
        expected = sample["expected"]

        for key, expected_value in expected.items():
            actual = attrs.get(key)
            if actual is None:
                raise SystemExit(f"{sample['label']} missing {key}")
            if key == "weight":
                if abs(float(actual) - float(expected_value)) > 1e-6:
                    raise SystemExit(f"{sample['label']} weight mismatch: {actual}")
                continue
            if actual != expected_value:
                raise SystemExit(
                    f"{sample['label']} {key} mismatch: {actual} != {expected_value}"
                )

print("ALL CHECKS PASSED")
PY

echo "=============================================="
echo "CAD Attribute Normalization Verification Complete"
echo "=============================================="
