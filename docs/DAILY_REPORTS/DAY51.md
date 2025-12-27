# Day 51 Report

Date: 2025-12-26

## Scope
- Full regression with Tenant Provisioning enabled.

## Work Completed
- Executed full `verify_all.sh` with platform admin and all optional CAD extractor checks enabled.

## Verification

Command:
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__tenant-1__org-1 \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
YUANTUS_PLATFORM_ADMIN_ENABLED=true \
YUANTUS_PLATFORM_TENANT_ID=platform \
YUANTUS_PLATFORM_ORG_ID=platform \
RUN_CAD_AUTO_PART=1 \
RUN_CAD_EXTRACTOR_STUB=1 \
RUN_CAD_EXTRACTOR_EXTERNAL=1 \
RUN_CAD_EXTRACTOR_SERVICE=1 \
RUN_TENANT_PROVISIONING=1 \
CAD_EXTRACTOR_BASE_URL=http://localhost:8200 \
CAD_EXTRACTOR_SAMPLE_FILE=/tmp/EXT-123-External-v2.dwg \
CAD_EXTRACTOR_EXPECT_KEY=part_number \
CAD_EXTRACTOR_EXPECT_VALUE=EXT-123-External \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Results:
- PASS: 39
- FAIL: 0
- SKIP: 0

Artifacts:
- docs/VERIFICATION_RESULTS.md (Run ALL-52)
