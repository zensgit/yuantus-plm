# Day 12 - S3 Deduped Upload Repair

## Scope
- Repair missing S3 objects when uploads are deduplicated by checksum.

## Changes
- When checksum dedupe hits but the storage object is missing, re-upload content.
- Applied to both CAD import and generic file upload flows.

## Verification

Command:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_PUBLIC_ENDPOINT_URL='http://localhost:59000' \
YUANTUS_S3_ACCESS_KEY_ID='minioadmin' \
YUANTUS_S3_SECRET_ACCESS_KEY='minioadmin' \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
Job processing: completed / completed
ALL CHECKS PASSED
```
