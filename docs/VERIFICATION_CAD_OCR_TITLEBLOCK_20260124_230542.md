# CAD OCR Title Block Verification (2026-01-24 23:05 +0800)

## 环境

- CAD ML Vision：`http://127.0.0.1:8000`
- Storage：S3 (MinIO)
- Tenancy：db-per-tenant-org

## 执行命令

```bash
CAD_ML_BASE_URL=http://127.0.0.1:8000 \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus" \
DB_URL_TEMPLATE="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}" \
IDENTITY_DB_URL="postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg" \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
bash scripts/verify_cad_ocr_titleblock.sh http://127.0.0.1:7910 tenant-1 org-1 \
  | tee docs/VERIFY_CAD_OCR_TITLEBLOCK_20260124_230542.log
```

## 结果摘要

- `verify_cad_ocr_titleblock.sh`：`ALL CHECKS PASSED`

## 日志

- `docs/VERIFY_CAD_OCR_TITLEBLOCK_20260124_230542.log`
