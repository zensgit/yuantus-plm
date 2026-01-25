# CADGF Preview Online Verification (2026-01-25 12:34 +0800)

## 执行命令

```bash
BASE_URL="http://127.0.0.1:7910" \
TENANT="tenant-1" ORG="org-1" \
LOGIN_USERNAME="admin" PASSWORD="admin" \
SAMPLE_FILE="/Users/huazhou/Downloads/Github/CADGameFusion/tests/plugin_data/importer_sample.dxf" \
CADGF_SYNC_GEOMETRY=1 \
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
scripts/verify_cad_preview_online.sh | tee docs/VERIFY_CADGF_PREVIEW_ONLINE_20260125_123457.log
```

## 结果摘要

- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- metadata_present: n/a
- report: `/tmp/cadgf_preview_online_report.md`

## 日志

- `docs/VERIFY_CADGF_PREVIEW_ONLINE_20260125_123457.log`
