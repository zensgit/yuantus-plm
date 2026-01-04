# CADGF Preview Bridge - Verification

## Environment
- Repo: `/Users/huazhou/Downloads/Github/Yuantus`

## Static Page Load (local)
```bash
PYTHONPATH=src python3 - <<'PY'
from yuantus.api.routers.cad_preview import _load_preview_html
html = _load_preview_html()
print("html_len", len(html))
print("has_form", "preview-form" in html)
PY
```
Result:
- `html_len` > 0
- `has_form` = True

## Bridge Smoke (local)
This run uses a Python 3.12 virtualenv to match `requirements.lock` and verifies the Yuantus proxy endpoints.

```bash
/opt/homebrew/bin/python3.12 -m venv /tmp/yuantus_plm_venv312
/tmp/yuantus_plm_venv312/bin/pip install -r /Users/huazhou/Downloads/Github/Yuantus/requirements.lock

cat <<'EOF' >/tmp/cadgf_plm_bridge_smoke.sh
#!/usr/bin/env bash
set -euo pipefail

CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
YUANTUS_ROOT="/Users/huazhou/Downloads/Github/Yuantus"
YUANTUS_VENV="/tmp/yuantus_plm_venv312"
YUANTUS_PORT="8010"

python3 "$CADGF_ROOT/tools/plm_router_service.py" \
  --host 127.0.0.1 --port 9000 \
  --default-plugin "$CADGF_ROOT/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib" \
  --default-convert-cli "$CADGF_ROOT/build_vcpkg/tools/convert_cli" \
  >/tmp/cadgf_router_step108.log 2>&1 &
ROUTER_PID=$!

PYTHONPATH="$YUANTUS_ROOT/src" "$YUANTUS_VENV/bin/uvicorn" yuantus.api.app:app \
  --host 127.0.0.1 --port "$YUANTUS_PORT" \
  >/tmp/yuantus_api_step108.log 2>&1 &
YUANTUS_PID=$!

cleanup() {
  kill "$ROUTER_PID" "$YUANTUS_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in {1..30}; do
  curl -s "http://127.0.0.1:9000/health" | grep -q '"ok"' && break
  sleep 1
done
for _ in {1..30}; do
  curl -s "http://127.0.0.1:${YUANTUS_PORT}/api/v1/health" | grep -q '"ok"' && break
  sleep 1
done

curl -s "http://127.0.0.1:${YUANTUS_PORT}/api/v1/cad-preview" | grep -q "preview-form"

RESP=$(curl -s -X POST "http://127.0.0.1:${YUANTUS_PORT}/api/v1/cad-preview/convert" \
  -F "file=@$CADGF_ROOT/tests/plugin_data/importer_sample.json" \
  -F "emit=json,gltf,meta" \
  -F "project_id=demo" \
  -F "document_label=sample")
echo "$RESP" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'

VIEWER_URL=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("viewer_url",""))' <<<"$RESP")
curl -s "$VIEWER_URL" | grep -q "Web Preview"
echo "bridge_smoke_ok"
EOF

bash /tmp/cadgf_plm_bridge_smoke.sh
```

Result:
- `bridge_smoke_ok`

## Public Base Rewrite Smoke (local)
This validates `YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL` rewrites viewer URLs while the
router remains on localhost.
Script: `scripts/verify_cad_preview_public_base.sh`

```bash
cat <<'EOF' >/tmp/yuantus_cadgf_public_base_smoke.sh
#!/usr/bin/env bash
set -euo pipefail

CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
YUANTUS_ROOT="/Users/huazhou/Downloads/Github/Yuantus"
YUANTUS_VENV="/tmp/yuantus_plm_venv312"
ROUTER_PORT=9100
YUANTUS_PORT=8100

export YUANTUS_DATABASE_URL="sqlite:////tmp/yuantus_cadgf_public_base.db"
export YUANTUS_LOCAL_STORAGE_PATH="/tmp/yuantus_cadgf_public_base_storage"
export YUANTUS_CADGF_ROUTER_BASE_URL="http://127.0.0.1:${ROUTER_PORT}"
export YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL="http://127.0.0.1:${ROUTER_PORT}/cadgf"

python3 "$CADGF_ROOT/tools/plm_router_service.py" \
  --host 127.0.0.1 --port "$ROUTER_PORT" \
  --default-plugin "$CADGF_ROOT/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib" \
  --default-convert-cli "$CADGF_ROOT/build_vcpkg/tools/convert_cli" \
  >/tmp/cadgf_router_public_base.log 2>&1 &
ROUTER_PID=$!

PYTHONPATH="$YUANTUS_ROOT/src" "$YUANTUS_VENV/bin/uvicorn" yuantus.api.app:app \
  --host 127.0.0.1 --port "$YUANTUS_PORT" \
  >/tmp/yuantus_api_public_base.log 2>&1 &
YUANTUS_PID=$!

cleanup() {
  kill "$ROUTER_PID" "$YUANTUS_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in {1..40}; do
  curl -s "http://127.0.0.1:${ROUTER_PORT}/health" | grep -q '"ok"' && break
  sleep 1
done
for _ in {1..40}; do
  curl -s "http://127.0.0.1:${YUANTUS_PORT}/api/v1/health" | grep -q '"ok"' && break
  sleep 1
done

curl -s "http://127.0.0.1:${YUANTUS_PORT}/api/v1/cad-preview" \
  | grep -Fq "routerBaseUrl: \\\"http://127.0.0.1:${ROUTER_PORT}/cadgf\\\""

RESP=$(curl -s -X POST "http://127.0.0.1:${YUANTUS_PORT}/api/v1/cad-preview/convert" \
  -F "file=@$CADGF_ROOT/tests/plugin_data/importer_sample.json" \
  -F "emit=json,gltf,meta" \
  -F "project_id=demo" \
  -F "document_label=sample")

STATUS=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("status"))' <<<"$RESP")
test "$STATUS" = "ok"

VIEWER_URL=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("viewer_url", ""))' <<<"$RESP")
case "$VIEWER_URL" in
  http://127.0.0.1:${ROUTER_PORT}/cadgf/*) ;;
  *) echo "viewer_url_mismatch:$VIEWER_URL" >&2; exit 1 ;;
esac

REAL_VIEWER_URL=${VIEWER_URL/\\/cadgf/}
curl -s "$REAL_VIEWER_URL" | grep -q "Web Preview"

echo "public_base_smoke_ok"
EOF

bash /tmp/yuantus_cadgf_public_base_smoke.sh
```

Result:
- `public_base_smoke_ok`

## Manifest Rewrite + CAD Assets (local)
Use a converted DXF file to ensure the rewritten manifest points to API URLs and the CAD asset endpoint resolves.

```bash
PYTHONPATH=src python3 - <<'PY'
import json
from types import SimpleNamespace
from yuantus.meta_engine.web import file_router

manifest = {"artifacts": {"mesh_gltf": "mesh.gltf"}}
dummy = SimpleNamespace(
    id="demo",
    cad_document_path="cadgf/demo/document.json",
    cad_metadata_path="cadgf/demo/mesh_metadata.json",
    geometry_path="cadgf/demo/mesh.gltf",
)

class DummyRequest:
    def url_for(self, name, **kwargs):
        base = "http://localhost:8010"
        if name == "get_cad_document":
            return f"{base}/api/v1/file/{kwargs['file_id']}/cad_document"
        if name == "get_cad_metadata":
            return f"{base}/api/v1/file/{kwargs['file_id']}/cad_metadata"
        if name == "get_cad_asset":
            return f"{base}/api/v1/file/{kwargs['file_id']}/cad_asset/{kwargs['asset_name']}"
        return base

rewritten = file_router._rewrite_cad_manifest_urls(DummyRequest(), dummy, manifest)
print(json.dumps(rewritten["artifacts"], indent=2, sort_keys=True))
PY
```

Result:
- `artifacts.mesh_gltf` is an absolute URL to `/api/v1/file/{id}/cad_asset/mesh.gltf`.
- `artifacts.document_json` and `artifacts.mesh_metadata` are absolute URLs.
Notes:
- Importing `file_router` may log "cadquery not installed..." in dev environments; it does not affect the rewrite output.

## Static Compile (local)
```bash
python3 -m py_compile \
  src/yuantus/api/app.py \
  src/yuantus/api/routers/cad_preview.py \
  src/yuantus/api/middleware/auth_enforce.py \
  src/yuantus/config/settings.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/cad_router.py
```

Result:
- `py_compile` completed without errors.

## Manual End-to-End (optional)
1. Start CADGameFusion router service:
   ```bash
   python3 /Users/huazhou/Downloads/Github/CADGameFusion/tools/plm_router_service.py \
     --host 127.0.0.1 --port 9000 \
     --default-plugin /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib \
     --default-convert-cli /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli
   ```
2. Start Yuantus API:
   ```bash
   PYTHONPATH=src uvicorn yuantus.api.app:app --reload --port 8000
   ```
3. Open:
   - `http://localhost:8000/api/v1/cad-preview`
4. Upload a sample file and confirm the preview iframe loads.

Notes:
- If router runs on a different host, update `YUANTUS_CADGF_ROUTER_BASE_URL`.
- If the browser needs a different base (reverse proxy), set `YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL`.
- If router auth is enabled, set `YUANTUS_CADGF_ROUTER_AUTH_TOKEN`.
- If port 8000 is in use, pick another port and update the URL.

## End-to-End CADGF Conversion + Viewer (local)
This run uses a temporary SQLite DB to avoid schema drift in existing dev databases.

```bash
export YUANTUS_DATABASE_URL="sqlite:////tmp/yuantus_cadgf_e2e.db"
export YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
export YUANTUS_CADGF_DXF_PLUGIN_PATH="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib"
export YUANTUS_CADGF_CONVERT_CLI="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli"
export YUANTUS_CADGF_ROUTER_BASE_URL="http://127.0.0.1:9000"
export YUANTUS_CAD_PREVIEW_PUBLIC="true"
export YUANTUS_CAD_PREVIEW_CORS_ORIGINS="http://127.0.0.1:9000"

python3 /Users/huazhou/Downloads/Github/CADGameFusion/tools/plm_router_service.py \
  --host 127.0.0.1 --port 9000 \
  --default-plugin /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib \
  --default-convert-cli /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli

PYTHONPATH=src /tmp/yuantus_plm_venv312/bin/uvicorn yuantus.api.app:app \
  --host 127.0.0.1 --port 8010
```

Upload a DXF:
```bash
curl -s -X POST "http://127.0.0.1:8010/api/v1/file/upload" \
  -F "file=@/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf"
```

Run CADGF conversion directly (cad_geometry):
```bash
PYTHONPATH=src /tmp/yuantus_plm_venv312/bin/python - <<'PY'
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.database import get_db_session
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_geometry
from yuantus.meta_engine.models.file import FileContainer

import_all_models()
with get_db_session() as session:
    file = session.query(FileContainer).order_by(FileContainer.created_at.desc()).first()
    result = cad_geometry({"file_id": file.id}, session)
    print(result)
PY
```

Verify manifest rewrite + viewer:
```bash
FILE_ID="<the uploaded file id>"
curl -s "http://127.0.0.1:8010/api/v1/file/${FILE_ID}" \
  | python3 - <<'PY'
import json,sys
data = json.load(sys.stdin)
print("cad_viewer_url", data.get("cad_viewer_url"))
PY

curl -s -H "Origin: http://127.0.0.1:9000" \
  "http://127.0.0.1:8010/api/v1/file/${FILE_ID}/cad_manifest?rewrite=1" \
  | python3 - <<'PY'
import json,sys
data = json.load(sys.stdin)
print("artifacts", data.get("artifacts", {}))
PY

CAD_VIEWER_URL=$(curl -s "http://127.0.0.1:8010/api/v1/file/${FILE_ID}" \
  | python3 - <<'PY'
import json,sys
data = json.load(sys.stdin)
print(data.get("cad_viewer_url", ""))
PY
)
curl -s "$CAD_VIEWER_URL" | grep -q "Web Preview"
```

Result:
- `cad_viewer_url` present and loads viewer HTML.
- `cad_manifest?rewrite=1` returns absolute URLs for `mesh_gltf` and `document_json`.
- CORS header present for `Origin: http://127.0.0.1:9000`.
- `mesh_metadata` may be absent depending on conversion output.

## Job Queue + Worker (local)
This runs the `cad_geometry` task through the JobWorker against a fresh SQLite DB.

```bash
export YUANTUS_ENVIRONMENT="dev"
export YUANTUS_DATABASE_URL="sqlite:////tmp/yuantus_cadgf_worker.db"
export YUANTUS_LOCAL_STORAGE_PATH="/tmp/yuantus_cadgf_storage"
export YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
export YUANTUS_CADGF_DXF_PLUGIN_PATH="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib"
export YUANTUS_CADGF_CONVERT_CLI="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli"

PYTHONPATH=src /tmp/yuantus_plm_venv312/bin/python - <<'PY'
import io
import uuid
from pathlib import Path

from yuantus.database import init_db, get_db_session
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.file import FileContainer, ConversionStatus
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.job_worker import JobWorker
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_geometry

CADGF_ROOT = Path("/Users/huazhou/Downloads/Github/CADGameFusion")
DXF_SAMPLE = CADGF_ROOT / "tests" / "plugin_data" / "importer_sample.dxf"

import_all_models()
init_db(create_tables=True)

file_id = str(uuid.uuid4())
file_bytes = DXF_SAMPLE.read_bytes()
file_ext = DXF_SAMPLE.suffix.lower()
storage_key = f"2d/{file_id[:2]}/{file_id}{file_ext}"

file_service = FileService()
file_service.upload_file(io.BytesIO(file_bytes), storage_key)

with get_db_session() as session:
    session.add(
        FileContainer(
            id=file_id,
            filename=DXF_SAMPLE.name,
            file_type=file_ext.lstrip("."),
            mime_type="image/vnd.dxf",
            file_size=len(file_bytes),
            checksum="",
            system_path=storage_key,
            document_type="2d",
            is_native_cad=True,
            cad_format="AUTOCAD",
            conversion_status=ConversionStatus.PENDING.value,
        )
    )

with get_db_session() as session:
    job_service = JobService(session)
    job = job_service.create_job(
        task_type="cad_geometry",
        payload={"file_id": file_id},
        priority=10,
    )
    print("job_created", job.id)

worker = JobWorker("verify-worker", poll_interval=1)
worker.register_handler("cad_geometry", cad_geometry)
print("worker_processed", worker.run_once())

with get_db_session() as session:
    file_container = session.get(FileContainer, file_id)
    print("cad_manifest_path", file_container.cad_manifest_path)
    print("geometry_path", file_container.geometry_path)
PY
```

Result:
- `worker_processed True`
- `cad_manifest_path` and `geometry_path` are populated.

Notes:
- The `cadquery not installed...` log is expected in dev if cadquery is not installed.
