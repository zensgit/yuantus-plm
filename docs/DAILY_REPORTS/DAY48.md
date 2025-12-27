# Day 48 Report

Date: 2025-01-10

## Scope
- Full regression run after compare_mode + ECO export metadata changes.

## Work Completed
- Ran the full verification suite via `scripts/verify_all.sh`.
- Captured PASS/FAIL/SKIP summary for Run ALL-13.

## Verification

Command:
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:5434/yuantus_tenant_1_org_1 \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:5434/yuantus_{tenant_id}_{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:5434/yuantus_identity \
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
RUN_CAD_AUTO_PART=0 \
RUN_CAD_EXTRACTOR_STUB=0 \
RUN_CAD_EXTRACTOR_EXTERNAL=0 \
RUN_CAD_EXTRACTOR_SERVICE=0 \
RUN_TENANT_PROVISIONING=0 \
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Results:
- PASS: 34
- FAIL: 0
- SKIP: 5

Artifacts:
- docs/VERIFICATION_RESULTS.md (Run ALL-13)
