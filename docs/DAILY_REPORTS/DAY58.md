# Day 58 Report

Date: 2025-12-26

## Scope
- Full regression with CAD real samples and real 2D connectors enabled.

## Work Completed
- Executed `verify_all.sh` with `RUN_CAD_REAL_CONNECTORS_2D=1` and `RUN_CAD_REAL_SAMPLES=1`.

## Verification

Command:
```
RUN_CAD_REAL_CONNECTORS_2D=1 \
RUN_CAD_REAL_SAMPLES=1 \
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
CAD_ML_BASE_URL=http://localhost:8001 \
CAD_REAL_FORCE_UNIQUE=1 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full7.log
```

Results:
- PASS: 41
- FAIL: 0
- SKIP: 0

Artifacts:
- docs/VERIFICATION_RESULTS.md (Run ALL-55)
- /tmp/verify_all_full7.log
