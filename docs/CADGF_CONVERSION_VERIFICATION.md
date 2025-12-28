# CADGameFusion 2D 转换验证记录

## 环境

- 时间：2025-01-06
- CADGameFusion：本地仓库（`/Users/huazhou/Downloads/Github/CADGameFusion`）
- Yuantus：本地仓库（`/Users/huazhou/Downloads/Github/Yuantus`）

## 验证 0：语法检查（局部）

命令（实际执行）：

```bash
python3 -m compileall \
  src/yuantus/meta_engine/services/cadgf_converter_service.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/cad_router.py
```

输出（实际）：

```text
Compiling 'src/yuantus/meta_engine/services/cadgf_converter_service.py'...
Compiling 'src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py'...
Compiling 'src/yuantus/meta_engine/web/file_router.py'...
Compiling 'src/yuantus/meta_engine/web/cad_router.py'...
```

## 验证 1：CADGF 转换服务（独立调用）

命令（实际执行）：

```bash
PYTHONPATH=src YUANTUS_CADGF_ROOT=/Users/huazhou/Downloads/Github/CADGameFusion \
  python3 - <<'PY'
from pathlib import Path
import json
import tempfile

from yuantus.meta_engine.services.cadgf_converter_service import CADGFConverterService

input_path = "/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf"
output_dir = Path(tempfile.mkdtemp(prefix="cadgf_verify_"))

svc = CADGFConverterService()
artifacts = svc.convert(input_path, str(output_dir), extension="dxf")

print(f"output_dir={output_dir}")
print(f"manifest_exists={artifacts.manifest_path.exists()}")
print(f"gltf_exists={bool(artifacts.mesh_gltf_path and artifacts.mesh_gltf_path.exists())}")
print(f"bin_exists={bool(artifacts.mesh_bin_path and artifacts.mesh_bin_path.exists())}")

if artifacts.mesh_gltf_path and artifacts.mesh_gltf_path.exists():
    with artifacts.mesh_gltf_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    buffers = data.get("buffers") or []
    uri = buffers[0].get("uri") if buffers else None
    print(f"buffer_uri={uri}")
PY
```

输出（实际）：

```text
output_dir=/var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/cadgf_verify_bxj8mola
manifest_exists=True
gltf_exists=True
bin_exists=True
buffer_uri=asset/mesh.bin
```

结论：

- CADGF 转换链路可用
- glTF 缓冲路径已按预期改写为 `asset/mesh.bin`

## 验证 2：cad_geometry 任务端到端（本地存储）

命令（实际执行）：

```bash
tmp_storage=$(mktemp -d)
tmp_db=$(mktemp -t yuantus_cadgf_test.db)
export YUANTUS_DATABASE_URL="sqlite:///$tmp_db"
export YUANTUS_LOCAL_STORAGE_PATH="$tmp_storage"
export YUANTUS_STORAGE_TYPE=local
export YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
PYTHONPATH=src python3 - <<'PY'
import json
import os
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from yuantus.database import create_db_engine
from yuantus.models.base import Base
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.file import FileContainer, DocumentType
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_geometry
from yuantus.security.rbac import models as _rbac_models  # noqa: F401
from yuantus.security.auth import models as _auth_models  # noqa: F401
from yuantus.models import user as _user_models  # noqa: F401

input_path = "/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf"

engine = create_db_engine(os.environ["YUANTUS_DATABASE_URL"])
import_all_models()
Base.metadata.create_all(engine)
session = Session(engine)

file_id = uuid.uuid4().hex
stored_filename = f"{file_id}.dxf"
storage_key = f"{DocumentType.CAD_2D.value}/{file_id[:2]}/{stored_filename}"

file_service = FileService()
with open(input_path, "rb") as handle:
    file_service.upload_file(handle, storage_key)

file_container = FileContainer(
    id=file_id,
    filename="importer_sample.dxf",
    file_type="dxf",
    mime_type="application/dxf",
    file_size=os.path.getsize(input_path),
    checksum="",
    system_path=storage_key,
    document_type=DocumentType.CAD_2D.value,
    is_native_cad=True,
    cad_format="AUTOCAD",
)
session.add(file_container)
session.commit()

result = cad_geometry({"file_id": file_id, "target_format": "gltf"}, session)
session.refresh(file_container)

storage_root = Path(os.environ["YUANTUS_LOCAL_STORAGE_PATH"])
geometry_abs = storage_root / file_container.geometry_path
manifest_abs = storage_root / file_container.cad_manifest_path
metadata_abs = (
    storage_root / file_container.cad_metadata_path
    if file_container.cad_metadata_path
    else None
)

doc_abs = (
    storage_root / file_container.cad_document_path
    if file_container.cad_document_path
    else None
)

buffer_uri = None
if geometry_abs.exists():
    with geometry_abs.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    buffers = data.get("buffers") or []
    if buffers:
        buffer_uri = buffers[0].get("uri")

print(f"storage_root={storage_root}")
print(f"db_url={os.environ['YUANTUS_DATABASE_URL']}")
print(f"result={result}")
print(f"geometry_path={file_container.geometry_path}")
print(f"cad_manifest_path={file_container.cad_manifest_path}")
print(f"cad_document_path={file_container.cad_document_path}")
print(f"cad_metadata_path={file_container.cad_metadata_path}")
print(f"geometry_exists={geometry_abs.exists()}")
print(f"manifest_exists={manifest_abs.exists()}")
print(f"document_exists={doc_abs.exists() if doc_abs else False}")
print(f"metadata_exists={metadata_abs.exists() if metadata_abs else False}")
print(f"buffer_uri={buffer_uri}")
PY
```

输出（实际）：

```text
storage_root=/var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/tmp.wOV9ZyllKw
db_url=sqlite:////var/folders/23/dzwf05nn7nvgxc1fz30kn5gh0000gn/T/yuantus_cadgf_test.db.UPDyHITN7h
result={'ok': True, 'file_id': '37c908f03c3b4d809ab7f6f3763c3182', 'geometry_path': 'cadgf/37/37c908f03c3b4d809ab7f6f3763c3182/mesh.gltf', 'geometry_url': '/api/v1/file/37c908f03c3b4d809ab7f6f3763c3182/geometry', 'cad_manifest_url': '/api/v1/file/37c908f03c3b4d809ab7f6f3763c3182/cad_manifest', 'cad_document_url': '/api/v1/file/37c908f03c3b4d809ab7f6f3763c3182/cad_document', 'cad_metadata_url': '/api/v1/file/37c908f03c3b4d809ab7f6f3763c3182/cad_metadata', 'target_format': 'gltf'}
geometry_path=cadgf/37/37c908f03c3b4d809ab7f6f3763c3182/mesh.gltf
cad_manifest_path=cadgf/37/37c908f03c3b4d809ab7f6f3763c3182/manifest.json
cad_document_path=cadgf/37/37c908f03c3b4d809ab7f6f3763c3182/document.json
cad_metadata_path=cadgf/37/37c908f03c3b4d809ab7f6f3763c3182/mesh_metadata.json
geometry_exists=True
manifest_exists=True
document_exists=True
metadata_exists=True
buffer_uri=asset/mesh.bin
```

结论：

- `cad_geometry` 对 DXF 能成功触发 CADGF 转换
- 产物路径落盘并回写到 `FileContainer`
- glTF buffer URI 与 asset 路径符合约定

## 验证 3：API + Worker 全链路（cad/import → cad_geometry）

命令（实际执行）：

```bash
tmp_storage=$(mktemp -d)
tmp_meta_db=$(mktemp -t yuantus_meta_api.db)
tmp_identity_db=$(mktemp -t yuantus_identity_api.db)
export YUANTUS_TENANCY_MODE=single
export YUANTUS_DATABASE_URL="sqlite:///$tmp_meta_db"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:///$tmp_identity_db"
export YUANTUS_LOCAL_STORAGE_PATH="$tmp_storage"
export YUANTUS_STORAGE_TYPE=local
export YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
export YUANTUS_PLUGINS_AUTOLOAD=false
PYTHONPATH=src python3 - <<'PY'
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import init_db, get_db_session
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.job_worker import JobWorker
from yuantus.meta_engine.tasks.cad_pipeline_tasks import (
    cad_dedup_vision,
    cad_extract,
    cad_geometry,
    cad_ml_vision,
    cad_preview,
)
from yuantus.security.auth.database import init_identity_db, get_identity_sessionmaker
from yuantus.security.auth.jwt import build_access_token_payload, encode_hs256
from yuantus.security.auth.service import AuthService

settings = get_settings()

init_db(create_tables=True)
init_identity_db(create_tables=True)

identity_session = get_identity_sessionmaker()()
auth = AuthService(identity_session)

tenant_id = "tenant-1"
org_id = "org-1"
username = "admin"
password = "admin"

try:
    auth.ensure_tenant(tenant_id, name=tenant_id)
    auth.ensure_org(tenant_id, org_id, name=org_id)
    user = auth.create_user(
        tenant_id=tenant_id,
        username=username,
        password=password,
        email="admin@example.com",
        is_superuser=True,
        user_id=1,
    )
except Exception:
    user = auth.authenticate(tenant_id=tenant_id, username=username, password=password)

auth.add_membership(tenant_id=tenant_id, org_id=org_id, user_id=user.id, roles=["admin"])
identity_session.commit()
identity_session.close()

payload = build_access_token_payload(
    user_id=user.id,
    tenant_id=tenant_id,
    org_id=org_id,
    ttl_seconds=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
)
token = encode_hs256(payload, secret=settings.JWT_SECRET_KEY)

app = create_app()
client = TestClient(app)

input_path = "/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf"
with open(input_path, "rb") as handle:
    response = client.post(
        "/api/v1/cad/import",
        headers={
            "Authorization": f"Bearer {token}",
            "x-tenant-id": tenant_id,
            "x-org-id": org_id,
        },
        files={"file": ("importer_sample.dxf", handle, "application/dxf")},
        data={
            "create_preview_job": "false",
            "create_geometry_job": "true",
            "create_extract_job": "false",
            "create_dedup_job": "false",
            "create_ml_job": "false",
            "geometry_format": "gltf",
        },
    )

print(f"import_status={response.status_code}")
print(f"import_response={response.json()}")

file_id = response.json().get("file_id")

worker = JobWorker("verify-worker", poll_interval=1)
worker.register_handler("cad_preview", cad_preview)
worker.register_handler("cad_geometry", cad_geometry)
worker.register_handler("cad_extract", cad_extract)
worker.register_handler("cad_dedup_vision", cad_dedup_vision)
worker.register_handler("cad_ml_vision", cad_ml_vision)
processed = worker.run_once()
print(f"worker_processed={processed}")

meta_response = client.get(
    f"/api/v1/file/{file_id}",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"meta_status={meta_response.status_code}")
print(f"meta_response={meta_response.json()}")

geometry_resp = client.get(
    f"/api/v1/file/{file_id}/geometry",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"geometry_status={geometry_resp.status_code}")
print(f"geometry_content_type={geometry_resp.headers.get('content-type')}")

asset_resp = client.get(
    f"/api/v1/file/{file_id}/asset/mesh.bin",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"asset_status={asset_resp.status_code}")
print(f"asset_content_type={asset_resp.headers.get('content-type')}")

manifest_resp = client.get(
    f"/api/v1/file/{file_id}/cad_manifest",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"manifest_status={manifest_resp.status_code}")

cad_doc_resp = client.get(
    f"/api/v1/file/{file_id}/cad_document",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"document_status={cad_doc_resp.status_code}")

metadata_resp = client.get(
    f"/api/v1/file/{file_id}/cad_metadata",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"metadata_status={metadata_resp.status_code}")

with get_db_session() as db:
    file_container = db.get(FileContainer, file_id)
    storage_root = Path(os.environ["YUANTUS_LOCAL_STORAGE_PATH"])
    geometry_abs = storage_root / (file_container.geometry_path or "")
    buffer_uri = None
    if geometry_abs.exists():
        with geometry_abs.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        buffers = data.get("buffers") or []
        if buffers:
            buffer_uri = buffers[0].get("uri")

    print(f"geometry_path={file_container.geometry_path}")
    print(f"cad_manifest_path={file_container.cad_manifest_path}")
    print(f"cad_document_path={file_container.cad_document_path}")
    print(f"cad_metadata_path={file_container.cad_metadata_path}")
    print(f"geometry_exists={geometry_abs.exists()}")
    print(f"buffer_uri={buffer_uri}")
PY
```

输出（实际）：

```text
import_status=200
import_response={'file_id': '20e523d8-8e08-4796-b6bc-389dd73abb67', 'filename': 'importer_sample.dxf', 'checksum': '115c5d41ef76282ac46fac49d3941b856715e930acff9d1f51280e419fd0bf27', 'is_duplicate': False, 'item_id': None, 'attachment_id': None, 'jobs': [{'id': 'c9eb25cb-b93f-4802-9571-b605771bd6b2', 'task_type': 'cad_geometry', 'status': 'pending'}], 'download_url': '/api/v1/file/20e523d8-8e08-4796-b6bc-389dd73abb67/download', 'preview_url': None, 'geometry_url': None, 'cad_manifest_url': None, 'cad_document_url': None, 'cad_metadata_url': None, 'cad_format': 'AUTOCAD', 'cad_connector_id': 'autocad', 'document_type': '2d', 'is_native_cad': True, 'author': None, 'source_system': None, 'source_version': None, 'document_version': None}
worker_processed=True
meta_status=200
meta_response={'id': '20e523d8-8e08-4796-b6bc-389dd73abb67', 'filename': 'importer_sample.dxf', 'file_type': 'dxf', 'mime_type': 'image/vnd.dxf', 'file_size': 124, 'checksum': '115c5d41ef76282ac46fac49d3941b856715e930acff9d1f51280e419fd0bf27', 'document_type': '2d', 'is_native_cad': True, 'cad_format': 'AUTOCAD', 'cad_connector_id': 'autocad', 'author': None, 'source_system': None, 'source_version': None, 'document_version': None, 'preview_url': None, 'geometry_url': '/api/v1/file/20e523d8-8e08-4796-b6bc-389dd73abb67/geometry', 'cad_manifest_url': '/api/v1/file/20e523d8-8e08-4796-b6bc-389dd73abb67/cad_manifest', 'cad_document_url': '/api/v1/file/20e523d8-8e08-4796-b6bc-389dd73abb67/cad_document', 'cad_metadata_url': '/api/v1/file/20e523d8-8e08-4796-b6bc-389dd73abb67/cad_metadata', 'conversion_status': 'completed', 'created_at': '2025-12-23T15:13:23'}
geometry_status=200
geometry_content_type=model/gltf+json
asset_status=200
asset_content_type=application/octet-stream
manifest_status=200
document_status=200
metadata_status=200
geometry_path=cadgf/20/20e523d8-8e08-4796-b6bc-389dd73abb67/mesh.gltf
cad_manifest_path=cadgf/20/20e523d8-8e08-4796-b6bc-389dd73abb67/manifest.json
cad_document_path=cadgf/20/20e523d8-8e08-4796-b6bc-389dd73abb67/document.json
cad_metadata_path=cadgf/20/20e523d8-8e08-4796-b6bc-389dd73abb67/mesh_metadata.json
geometry_exists=True
buffer_uri=asset/mesh.bin
```

结论：

- `POST /api/v1/cad/import` 可触发 `cad_geometry` 任务
- Worker 成功处理任务并产出 CADGF 文件
- `geometry`/`asset`/`cad_manifest`/`cad_document`/`cad_metadata` 均可访问
- glTF buffer URI 与 asset 约定一致

## 验证 4：S3/MinIO 路径（API + Worker）

命令（实际执行）：

```bash
tmp_meta_db=$(mktemp -t yuantus_meta_s3.db)
tmp_identity_db=$(mktemp -t yuantus_identity_s3.db)
export YUANTUS_TENANCY_MODE=single
export YUANTUS_DATABASE_URL="sqlite:///$tmp_meta_db"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:///$tmp_identity_db"
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL="http://localhost:59000"
export YUANTUS_S3_PUBLIC_ENDPOINT_URL="http://localhost:59000"
export YUANTUS_S3_BUCKET_NAME=yuantus
export YUANTUS_S3_ACCESS_KEY_ID=minioadmin
export YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin
export YUANTUS_S3_REGION_NAME=us-east-1
export YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
export YUANTUS_PLUGINS_AUTOLOAD=false
PYTHONPATH=src python3 - <<'PY'
import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import init_db, get_db_session
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.job_worker import JobWorker
from yuantus.meta_engine.tasks.cad_pipeline_tasks import (
    cad_dedup_vision,
    cad_extract,
    cad_geometry,
    cad_ml_vision,
    cad_preview,
)
from yuantus.security.auth.database import init_identity_db, get_identity_sessionmaker
from yuantus.security.auth.jwt import build_access_token_payload, encode_hs256
from yuantus.security.auth.service import AuthService

settings = get_settings()

s3 = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
    aws_access_key_id=settings.S3_ACCESS_KEY_ID,
    aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
    region_name=settings.S3_REGION_NAME,
)

bucket = settings.S3_BUCKET_NAME
try:
    s3.head_bucket(Bucket=bucket)
except ClientError:
    s3.create_bucket(Bucket=bucket)

init_db(create_tables=True)
init_identity_db(create_tables=True)

identity_session = get_identity_sessionmaker()()
auth = AuthService(identity_session)

tenant_id = "tenant-1"
org_id = "org-1"
username = "admin"
password = "admin"

try:
    auth.ensure_tenant(tenant_id, name=tenant_id)
    auth.ensure_org(tenant_id, org_id, name=org_id)
    user = auth.create_user(
        tenant_id=tenant_id,
        username=username,
        password=password,
        email="admin@example.com",
        is_superuser=True,
        user_id=1,
    )
except Exception:
    user = auth.authenticate(tenant_id=tenant_id, username=username, password=password)

auth.add_membership(tenant_id=tenant_id, org_id=org_id, user_id=user.id, roles=["admin"])
identity_session.commit()
identity_session.close()

payload = build_access_token_payload(
    user_id=user.id,
    tenant_id=tenant_id,
    org_id=org_id,
    ttl_seconds=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
)
token = encode_hs256(payload, secret=settings.JWT_SECRET_KEY)

app = create_app()
client = TestClient(app)

input_path = "/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf"
with open(input_path, "rb") as handle:
    response = client.post(
        "/api/v1/cad/import",
        headers={
            "Authorization": f"Bearer {token}",
            "x-tenant-id": tenant_id,
            "x-org-id": org_id,
        },
        files={"file": ("importer_sample.dxf", handle, "application/dxf")},
        data={
            "create_preview_job": "false",
            "create_geometry_job": "true",
            "create_extract_job": "false",
            "create_dedup_job": "false",
            "create_ml_job": "false",
            "geometry_format": "gltf",
        },
    )

print(f"import_status={response.status_code}")
print(f"import_response={response.json()}")

file_id = response.json().get("file_id")

worker = JobWorker("verify-worker", poll_interval=1)
worker.register_handler("cad_preview", cad_preview)
worker.register_handler("cad_geometry", cad_geometry)
worker.register_handler("cad_extract", cad_extract)
worker.register_handler("cad_dedup_vision", cad_dedup_vision)
worker.register_handler("cad_ml_vision", cad_ml_vision)
processed = worker.run_once()
print(f"worker_processed={processed}")

meta_response = client.get(
    f"/api/v1/file/{file_id}",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
)
print(f"meta_status={meta_response.status_code}")
print(f"meta_response={meta_response.json()}")

geometry_resp = client.get(
    f"/api/v1/file/{file_id}/geometry",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
    follow_redirects=False,
)
print(f"geometry_status={geometry_resp.status_code}")
print(f\"geometry_location={geometry_resp.headers.get('location')}\")

asset_resp = client.get(
    f\"/api/v1/file/{file_id}/asset/mesh.bin\",
    headers={
        \"Authorization\": f\"Bearer {token}\",
        \"x-tenant-id\": tenant_id,
        \"x-org-id\": org_id,
    },
    follow_redirects=False,
)
print(f\"asset_status={asset_resp.status_code}\")
print(f\"asset_location={asset_resp.headers.get('location')}\")

manifest_resp = client.get(
    f\"/api/v1/file/{file_id}/cad_manifest\",
    headers={
        \"Authorization\": f\"Bearer {token}\",
        \"x-tenant-id\": tenant_id,
        \"x-org-id\": org_id,
    },
    follow_redirects=False,
)
print(f\"manifest_status={manifest_resp.status_code}\")

cad_doc_resp = client.get(
    f\"/api/v1/file/{file_id}/cad_document\",
    headers={
        \"Authorization\": f\"Bearer {token}\",
        \"x-tenant-id\": tenant_id,
        \"x-org-id\": org_id,
    },
    follow_redirects=False,
)
print(f\"document_status={cad_doc_resp.status_code}\")

metadata_resp = client.get(
    f\"/api/v1/file/{file_id}/cad_metadata\",
    headers={
        \"Authorization\": f\"Bearer {token}\",
        \"x-tenant-id\": tenant_id,
        \"x-org-id\": org_id,
    },
    follow_redirects=False,
)
print(f\"metadata_status={metadata_resp.status_code}\")

with get_db_session() as db:
    file_container = db.get(FileContainer, file_id)
    print(f\"geometry_path={file_container.geometry_path}\")
    print(f\"cad_manifest_path={file_container.cad_manifest_path}\")
    print(f\"cad_document_path={file_container.cad_document_path}\")
    print(f\"cad_metadata_path={file_container.cad_metadata_path}\")

    buffer_uri = None
    if file_container.geometry_path:
        obj = s3.get_object(Bucket=bucket, Key=file_container.geometry_path)
        data = json.loads(obj[\"Body\"].read().decode(\"utf-8\"))
        buffers = data.get(\"buffers\") or []
        if buffers:
            buffer_uri = buffers[0].get(\"uri\")
    print(f\"buffer_uri={buffer_uri}\")
PY
```

输出（实际）：

```text
import_status=200
import_response={'file_id': 'cdee5989-de9f-4439-b660-6c3721b8d587', 'filename': 'importer_sample.dxf', 'checksum': '115c5d41ef76282ac46fac49d3941b856715e930acff9d1f51280e419fd0bf27', 'is_duplicate': False, 'item_id': None, 'attachment_id': None, 'jobs': [{'id': '32d488aa-e13f-4427-9184-78bd25920d7e', 'task_type': 'cad_geometry', 'status': 'pending'}], 'download_url': '/api/v1/file/cdee5989-de9f-4439-b660-6c3721b8d587/download', 'preview_url': None, 'geometry_url': None, 'cad_manifest_url': None, 'cad_document_url': None, 'cad_metadata_url': None, 'cad_format': 'AUTOCAD', 'cad_connector_id': 'autocad', 'document_type': '2d', 'is_native_cad': True, 'author': None, 'source_system': None, 'source_version': None, 'document_version': None}
worker_processed=True
meta_status=200
meta_response={'id': 'cdee5989-de9f-4439-b660-6c3721b8d587', 'filename': 'importer_sample.dxf', 'file_type': 'dxf', 'mime_type': 'image/vnd.dxf', 'file_size': 124, 'checksum': '115c5d41ef76282ac46fac49d3941b856715e930acff9d1f51280e419fd0bf27', 'document_type': '2d', 'is_native_cad': True, 'cad_format': 'AUTOCAD', 'cad_connector_id': 'autocad', 'author': None, 'source_system': None, 'source_version': None, 'document_version': None, 'preview_url': None, 'geometry_url': '/api/v1/file/cdee5989-de9f-4439-b660-6c3721b8d587/geometry', 'cad_manifest_url': '/api/v1/file/cdee5989-de9f-4439-b660-6c3721b8d587/cad_manifest', 'cad_document_url': '/api/v1/file/cdee5989-de9f-4439-b660-6c3721b8d587/cad_document', 'cad_metadata_url': '/api/v1/file/cdee5989-de9f-4439-b660-6c3721b8d587/cad_metadata', 'conversion_status': 'completed', 'created_at': '2025-12-23T15:17:35'}
geometry_status=302
geometry_location=http://localhost:59000/yuantus/cadgf/cd/cdee5989-de9f-4439-b660-6c3721b8d587/mesh.gltf?AWSAccessKeyId=minioadmin&Signature=eoD8Foe5XHgJDcZuIy1pZ%2BAE3iM%3D&Expires=1766506655
asset_status=302
asset_location=http://localhost:59000/yuantus/cadgf/cd/cdee5989-de9f-4439-b660-6c3721b8d587/mesh.bin?AWSAccessKeyId=minioadmin&Signature=b7vY2FDCk6AWupROnW3gPLZzMSM%3D&Expires=1766506655
manifest_status=302
document_status=302
metadata_status=302
geometry_path=cadgf/cd/cdee5989-de9f-4439-b660-6c3721b8d587/mesh.gltf
cad_manifest_path=cadgf/cd/cdee5989-de9f-4439-b660-6c3721b8d587/manifest.json
cad_document_path=cadgf/cd/cdee5989-de9f-4439-b660-6c3721b8d587/document.json
cad_metadata_path=cadgf/cd/cdee5989-de9f-4439-b660-6c3721b8d587/mesh_metadata.json
buffer_uri=asset/mesh.bin
```

结论：

- S3/MinIO 环境下 `cad_geometry` 可完成 CADGF 产物上传
- `geometry`/`asset`/`cad_manifest`/`cad_document`/`cad_metadata` 均返回 302 预签名 URL
- glTF buffer URI 与 asset 约定一致

## 验证 5：S3 预签名 URL 实际可读（follow）

命令（实际执行）：

```bash
tmp_meta_db=$(mktemp -t yuantus_meta_s3_follow.db)
tmp_identity_db=$(mktemp -t yuantus_identity_s3_follow.db)
export YUANTUS_TENANCY_MODE=single
export YUANTUS_DATABASE_URL="sqlite:///$tmp_meta_db"
export YUANTUS_IDENTITY_DATABASE_URL="sqlite:///$tmp_identity_db"
export YUANTUS_STORAGE_TYPE=s3
export YUANTUS_S3_ENDPOINT_URL="http://localhost:59000"
export YUANTUS_S3_PUBLIC_ENDPOINT_URL="http://localhost:59000"
export YUANTUS_S3_BUCKET_NAME=yuantus
export YUANTUS_S3_ACCESS_KEY_ID=minioadmin
export YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin
export YUANTUS_S3_REGION_NAME=us-east-1
export YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion"
export YUANTUS_PLUGINS_AUTOLOAD=false
PYTHONPATH=src python3 - <<'PY'
import json
import os
import urllib.request

import boto3
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import init_db
from yuantus.meta_engine.services.job_worker import JobWorker
from yuantus.meta_engine.tasks.cad_pipeline_tasks import (
    cad_dedup_vision,
    cad_extract,
    cad_geometry,
    cad_ml_vision,
    cad_preview,
)
from yuantus.security.auth.database import init_identity_db, get_identity_sessionmaker
from yuantus.security.auth.jwt import build_access_token_payload, encode_hs256
from yuantus.security.auth.service import AuthService

settings = get_settings()

s3 = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
    aws_access_key_id=settings.S3_ACCESS_KEY_ID,
    aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
    region_name=settings.S3_REGION_NAME,
)

bucket = settings.S3_BUCKET_NAME
try:
    s3.head_bucket(Bucket=bucket)
except ClientError:
    s3.create_bucket(Bucket=bucket)

init_db(create_tables=True)
init_identity_db(create_tables=True)

identity_session = get_identity_sessionmaker()()
auth = AuthService(identity_session)

tenant_id = "tenant-1"
org_id = "org-1"
username = "admin"
password = "admin"

try:
    auth.ensure_tenant(tenant_id, name=tenant_id)
    auth.ensure_org(tenant_id, org_id, name=org_id)
    user = auth.create_user(
        tenant_id=tenant_id,
        username=username,
        password=password,
        email="admin@example.com",
        is_superuser=True,
        user_id=1,
    )
except Exception:
    user = auth.authenticate(tenant_id=tenant_id, username=username, password=password)

auth.add_membership(tenant_id=tenant_id, org_id=org_id, user_id=user.id, roles=["admin"])
identity_session.commit()
identity_session.close()

payload = build_access_token_payload(
    user_id=user.id,
    tenant_id=tenant_id,
    org_id=org_id,
    ttl_seconds=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
)
token = encode_hs256(payload, secret=settings.JWT_SECRET_KEY)

app = create_app()
client = TestClient(app)

input_path = "/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf"
with open(input_path, "rb") as handle:
    response = client.post(
        "/api/v1/cad/import",
        headers={
            "Authorization": f"Bearer {token}",
            "x-tenant-id": tenant_id,
            "x-org-id": org_id,
        },
        files={"file": ("importer_sample.dxf", handle, "application/dxf")},
        data={
            "create_preview_job": "false",
            "create_geometry_job": "true",
            "create_extract_job": "false",
            "create_dedup_job": "false",
            "create_ml_job": "false",
            "geometry_format": "gltf",
        },
    )

print(f"import_status={response.status_code}")
print(f"import_response={response.json()}")

file_id = response.json().get("file_id")

worker = JobWorker("verify-worker", poll_interval=1)
worker.register_handler("cad_preview", cad_preview)
worker.register_handler("cad_geometry", cad_geometry)
worker.register_handler("cad_extract", cad_extract)
worker.register_handler("cad_dedup_vision", cad_dedup_vision)
worker.register_handler("cad_ml_vision", cad_ml_vision)
processed = worker.run_once()
print(f"worker_processed={processed}")

geometry_resp = client.get(
    f"/api/v1/file/{file_id}/geometry",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
    follow_redirects=False,
)
geometry_url = geometry_resp.headers.get("location")
print(f"geometry_status={geometry_resp.status_code}")
print(f"geometry_location={geometry_url}")

asset_resp = client.get(
    f"/api/v1/file/{file_id}/asset/mesh.bin",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
    follow_redirects=False,
)
asset_url = asset_resp.headers.get("location")
print(f"asset_status={asset_resp.status_code}")
print(f"asset_location={asset_url}")

manifest_resp = client.get(
    f"/api/v1/file/{file_id}/cad_manifest",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
    follow_redirects=False,
)
manifest_url = manifest_resp.headers.get("location")
print(f"manifest_status={manifest_resp.status_code}")

cad_doc_resp = client.get(
    f"/api/v1/file/{file_id}/cad_document",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
    follow_redirects=False,
)
document_url = cad_doc_resp.headers.get("location")
print(f"document_status={cad_doc_resp.status_code}")

metadata_resp = client.get(
    f"/api/v1/file/{file_id}/cad_metadata",
    headers={
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id,
        "x-org-id": org_id,
    },
    follow_redirects=False,
)
metadata_url = metadata_resp.headers.get("location")
print(f"metadata_status={metadata_resp.status_code}")

def _fetch(url: str) -> bytes:
    if not url:
        return b""
    with urllib.request.urlopen(url) as resp:
        return resp.read()

geometry_bytes = _fetch(geometry_url)
asset_bytes = _fetch(asset_url)
manifest_bytes = _fetch(manifest_url)
metadata_bytes = _fetch(metadata_url)

manifest = json.loads(manifest_bytes.decode("utf-8")) if manifest_bytes else {}

print(f"geometry_fetch_bytes={len(geometry_bytes)}")
print(f"asset_fetch_bytes={len(asset_bytes)}")
print(f"manifest_fetch_bytes={len(manifest_bytes)}")
print(f"metadata_fetch_bytes={len(metadata_bytes)}")
print(f"manifest_status={manifest.get('status')}")
print(f"manifest_artifacts={manifest.get('artifacts')}")
PY
```

输出（实际）：

```text
import_status=200
import_response={'file_id': '098349ca-d6b8-4e7b-bd41-333dcccfd525', 'filename': 'importer_sample.dxf', 'checksum': '115c5d41ef76282ac46fac49d3941b856715e930acff9d1f51280e419fd0bf27', 'is_duplicate': False, 'item_id': None, 'attachment_id': None, 'jobs': [{'id': 'c9dcc7b7-3dca-4b41-873a-1f47936fe7ad', 'task_type': 'cad_geometry', 'status': 'pending'}], 'download_url': '/api/v1/file/098349ca-d6b8-4e7b-bd41-333dcccfd525/download', 'preview_url': None, 'geometry_url': None, 'cad_manifest_url': None, 'cad_document_url': None, 'cad_metadata_url': None, 'cad_format': 'AUTOCAD', 'cad_connector_id': 'autocad', 'document_type': '2d', 'is_native_cad': True, 'author': None, 'source_system': None, 'source_version': None, 'document_version': None}
worker_processed=True
geometry_status=302
geometry_location=http://localhost:59000/yuantus/cadgf/09/098349ca-d6b8-4e7b-bd41-333dcccfd525/mesh.gltf?AWSAccessKeyId=minioadmin&Signature=vhtvLiIovfyqPtOHl73NMMrp6K8%3D&Expires=1766506851
asset_status=302
asset_location=http://localhost:59000/yuantus/cadgf/09/098349ca-d6b8-4e7b-bd41-333dcccfd525/mesh.bin?AWSAccessKeyId=minioadmin&Signature=Ng1LVDnAfZi7hnQ1Guqge%2B7sCFM%3D&Expires=1766506851
manifest_status=302
document_status=302
metadata_status=302
geometry_fetch_bytes=1048
asset_fetch_bytes=72
manifest_fetch_bytes=529
metadata_fetch_bytes=183
manifest_status=ok
manifest_artifacts={'document_json': 'document.json', 'mesh_gltf': 'mesh.gltf', 'mesh_bin': 'mesh.bin', 'mesh_metadata': 'mesh_metadata.json'}
```

结论：

- 预签名 URL 可实际读取对象内容
- glTF/mesh.bin/manifest/metadata 均有非 0 字节输出
