#!/usr/bin/env bash
# =============================================================================
# CAD Filename Parsing Verification Script
# Verifies: filename-based part_number/part_name/revision/drawing_no extraction
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

DB_PATH="/tmp/yuantus_cad_filename_parse.db"
STORAGE_PATH="/tmp/yuantus_cad_filename_storage"

rm -f "$DB_PATH"
rm -rf "$STORAGE_PATH"

echo "=============================================="
echo "CAD Filename Parsing Verification"
echo "DB: $DB_PATH"
echo "Storage: $STORAGE_PATH"
echo "=============================================="

YUANTUS_DATABASE_URL="sqlite:///$DB_PATH" \
YUANTUS_SCHEMA_MODE="create_all" \
YUANTUS_TENANCY_MODE="single" \
YUANTUS_LOCAL_STORAGE_PATH="$STORAGE_PATH" \
"$PY" - <<'PY'
import io
import os
import uuid
import hashlib

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.database import init_db, get_db_session
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.cad_service import CadService

import_all_models()
init_db(create_tables=True)

samples = [
    {
        "filename": "model2.prt.1",
        "file_type": "prt",
        "document_type": "3d",
        "expect": {
            "part_number": "model2",
            "revision": "1",
        },
    },
    {
        "filename": "J2824002-06上封头组件v2.dwg",
        "file_type": "dwg",
        "document_type": "2d",
        "expect": {
            "part_number": "J2824002-06",
            "drawing_no": "J2824002-06",
            "part_name": "上封头组件",
            "revision": "v2",
        },
    },
    {
        "filename": "比较_J2825002-09下轴承支架组件v2.dwg",
        "file_type": "dwg",
        "document_type": "2d",
        "expect": {
            "part_number": "J2825002-09",
            "drawing_no": "J2825002-09",
            "part_name": "下轴承支架组件",
            "revision": "v2",
        },
    },
]

file_service = FileService()
cad_service = CadService(None)

def upload_sample(name: str) -> str:
    content = f"dummy:{name}".encode("utf-8")
    checksum = hashlib.sha256(content).hexdigest()
    file_id = str(uuid.uuid4())
    storage_key = f"cad/{file_id}/{name}"
    file_service.upload_file(io.BytesIO(content), storage_key)
    return file_id, storage_key, len(content), checksum

with get_db_session() as session:
    cad_service.session = session
    for sample in samples:
        file_id, storage_key, size, checksum = upload_sample(sample["filename"])
        file_container = FileContainer(
            id=file_id,
            filename=sample["filename"],
            file_type=sample["file_type"],
            mime_type="application/octet-stream",
            file_size=size,
            checksum=checksum,
            system_path=storage_key,
            document_type=sample["document_type"],
            is_native_cad=True,
        )
        session.add(file_container)
        session.commit()

        attrs, source = cad_service.extract_attributes_for_file(
            file_container, file_service=file_service, return_source=True
        )

        expected = sample["expect"]
        for key, value in expected.items():
            actual = attrs.get(key)
            if actual is None:
                raise SystemExit(f"{sample['filename']} missing {key}")
            if str(actual) != str(value):
                raise SystemExit(
                    f"{sample['filename']} {key} mismatch: {actual} != {value}"
                )

        if source not in {"local", "external"}:
            raise SystemExit(f"{sample['filename']} unexpected source: {source}")

print("ALL CHECKS PASSED")
PY

echo "=============================================="
echo "CAD Filename Parsing Verification Complete"
echo "=============================================="
