# Full Regression Verification (2026-01-25 12:41 +0800)

## 范围

- scripts/verify_all.sh 全量回归（HTTP + Docker 运行环境）
- 启用 CADGF 在线预览（RUN_CADGF_PREVIEW_ONLINE=1，CADGF Sync Geometry 回退）
- 开启标志：
  - RUN_UI_AGG=1
  - RUN_OPS_S8=1
  - RUN_TENANT_PROVISIONING=1
  - RUN_CAD_REAL_CONNECTORS_2D=1
  - RUN_CAD_CONNECTOR_COVERAGE_2D=1
  - RUN_CAD_AUTO_PART=1
  - RUN_CAD_EXTRACTOR_STUB=1
  - RUN_CAD_EXTRACTOR_EXTERNAL=1
  - RUN_CAD_EXTRACTOR_SERVICE=1
  - RUN_CAD_REAL_SAMPLES=1
  - RUN_CADGF_PREVIEW_ONLINE=1

## 执行步骤

### 1) 启动 CADGF router

```bash
python3 -u /Users/huazhou/Downloads/Github/CADGameFusion/tools/plm_router_service.py \
  --host 127.0.0.1 --port 9000 \
  --default-plugin /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib \
  --default-convert-cli /Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli
```

### 2) 全量回归

```bash
RUN_UI_AGG=1 RUN_OPS_S8=1 RUN_TENANT_PROVISIONING=1 \
RUN_CAD_REAL_CONNECTORS_2D=1 RUN_CAD_CONNECTOR_COVERAGE_2D=1 RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 RUN_CAD_EXTRACTOR_EXTERNAL=1 RUN_CAD_EXTRACTOR_SERVICE=1 RUN_CAD_REAL_SAMPLES=1 \
RUN_CADGF_PREVIEW_ONLINE=1 CADGF_SYNC_GEOMETRY=1 \
CADGF_PREVIEW_SAMPLE_FILE="/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf" \
CAD_ML_BASE_URL=http://127.0.0.1:8000 \
CAD_EXTRACTOR_BASE_URL=http://127.0.0.1:8200 \
CAD_CONNECTOR_COVERAGE_DIR="/Users/huazhou/Downloads/训练图纸/训练图纸" \
CAD_CONNECTOR_COVERAGE_MAX_FILES=50 \
CAD_EXTRACTOR_SAMPLE_FILE="/Users/huazhou/Downloads/训练图纸/训练图纸/J0724006-01下锥体组件v3.dwg" \
CAD_SAMPLE_DWG="/Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg" \
CAD_SAMPLE_STEP="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/CNC.stp" \
CAD_SAMPLE_PRT="/Users/huazhou/Downloads/4000例CAD及三维机械零件练习图纸/机械CAD图纸/三维出二维图/model2.prt" \
CAD_REAL_FORCE_UNIQUE=1 CAD_EXTRACTOR_ALLOW_EMPTY=1 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus" \
YUANTUS_DATABASE_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}" \
YUANTUS_IDENTITY_DATABASE_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg" \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_CADGF_ROOT="/Users/huazhou/Downloads/Github/CADGameFusion" \
YUANTUS_CADGF_CONVERT_CLI="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/tools/convert_cli" \
YUANTUS_CADGF_DXF_PLUGIN_PATH="/Users/huazhou/Downloads/Github/CADGameFusion/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib" \
YUANTUS_CADGF_DEFAULT_EMIT="json,gltf,meta" \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_ALL_HTTP_20260125_124121.log
```

## 结果摘要

- PASS: 52
- FAIL: 0
- SKIP: 0

## 日志

- `docs/VERIFY_ALL_HTTP_20260125_124121.log`
