# Day 31 - ECO Impact Analysis (BOM Diff Linkage)

## Scope
- Extend ECO impact verification to include bom_diff in impact payload.
- Validate where-used + files + bom_diff linkage in a single impact call.

## Verification

Command:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- ECO Stage: 937c7443-d7d0-45be-aa70-686f344d3632
- ECO1: 3e6395b8-23ea-42bf-a45a-ccb7f8af5428
- ECO2: b350df1b-51cf-4dcd-ad88-1b50f1039b4a
- Product: 326e7a64-4655-4add-bc3c-2603047e20fb
- Source Version: b577a733-0d92-4229-8985-0fd9d36cf06f
- Target Version: 498ab678-e1b4-474a-a497-07061db5ec67

## Additional Verification - Version Diff in Impact

Command:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- ECO Stage: 3c96202e-0bc3-449f-8a87-51482c3db1ad
- ECO1: bd54086d-0d58-44e7-821f-997bc44ed0c7
- ECO2: 9369ef9e-db4e-4c41-a636-3f2c99f869db
- Product: 33767c45-1384-4e1c-893f-3292fda47ea5
- Source Version: 7c12dca9-c80f-4c31-b372-a6b3203a9b37
- Target Version: 902b4b33-afc1-4adb-9328-4ac420694538

## Additional Verification - Impact Export (CSV/XLSX/PDF)

Command:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- ECO Stage: 9f13af28-8ca6-4242-a849-2568b800c497
- ECO1: 368943ca-7dd9-4e23-b88a-d8128851d46f
- ECO2: 578272e5-8423-4efa-a81c-30f569bd720b
- Product: 29744ca9-f5d8-4c5c-a12a-4e1fc547d34e
- Assembly: 068744d3-9fd2-4c34-a516-7808dab76b81
- Source Version: a771b84f-cf9b-4ee1-a291-5c8639db1436
- Target Version: eb301ef8-928c-4624-88ab-8d0c88c2122d

## Additional Verification - Full Regression (verify_all.sh)

Command:

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_SCHEMA_MODE=migrations \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL TESTS PASSED (PASS=25, FAIL=0, SKIP=0)
```

Notes:
- Document: d7600cc4-f9bb-48dd-8bf5-0e9fb2345503
- Part (lifecycle): b1878353-b699-41f7-b872-79cdae2703b3
- CAD File (S5-A): 9a7dad67-2ac2-46f1-bbb7-b3119f48c533

## Additional Verification - Backup/Restore

Command:

```bash
PROJECT=yuantusplm BACKUP_DIR=/tmp/yuantus_backup_verify_1766467544 \
  bash scripts/verify_backup_restore.sh
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Backup dir: /tmp/yuantus_backup_verify_1766467544
- Restore DB suffix: _restore_1766467544
- Restore bucket: yuantus-restore-test-1766467544

## Additional Verification - Backup Rotation

Command:

```bash
bash scripts/verify_backup_rotation.sh
```

Result:

```text
ALL CHECKS PASSED
```

## Additional Verification - Audit Retention

Command:

```bash
AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

## Additional Verification - Quota Enforce

Command:

```bash
bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

## Additional Verification - Multi-Tenancy (db-per-tenant-org)

Command:

```bash
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
```

Result:

```text
ALL CHECKS PASSED
```

## Additional Verification - Full Regression (quota enforce + audit retention)

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_SCHEMA_MODE=migrations \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL TESTS PASSED (PASS=25, FAIL=0, SKIP=0)
```

## Additional Verification - Cleanup Restore

Command:

```bash
bash scripts/verify_cleanup_restore.sh
```

Result:

```text
ALL CHECKS PASSED
```

## Additional Verification - CAD 2D Connectors (Auto-detect, CN keys)

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- GStarCAD File: e2f659b9-59d2-44b8-a1d3-54497bcc169f
- ZWCAD File: 6904c7cf-b65b-4fba-a71e-10dba3c390cc
- Haochen File: 641ee1f9-bd21-4341-88a3-3bbb2194e57a
- Zhongwang File: 08df1968-5d40-40e0-881c-66b3ef463227
- Auto-detect File: 55bae091-624b-4ea7-88f5-cb93f14e151c

## Additional Verification - CAD Attribute Sync (S3 worker env)

Command:

```bash
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_sync.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Item: 628a5f85-b8cd-45fb-9f2d-ffbf75e17d88
- File: b1078ffb-fc5a-47ee-96e4-6d39c8717852
- Job: cdc8a2f3-40b0-4d6f-aecc-48b067a10da7

## Additional Verification - CAD Extract Local (CN keys)

Command:

```bash
bash scripts/verify_cad_extract_local.sh
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- cadquery not installed (warning only)

## Additional Verification - Full Regression (verify_all.sh, single + S3 env)

Command:

```bash
YUANTUS_STORAGE_TYPE=s3 \
YUANTUS_S3_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_PUBLIC_ENDPOINT_URL=http://localhost:59000 \
YUANTUS_S3_BUCKET_NAME=yuantus \
YUANTUS_S3_ACCESS_KEY_ID=minioadmin \
YUANTUS_S3_SECRET_ACCESS_KEY=minioadmin \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL TESTS PASSED (PASS=23, FAIL=0, SKIP=2)
```

Notes:
- Document: eab43e0d-1803-46ef-9953-06070dbb3133
- Part (lifecycle): c14fe667-dde7-4a46-9658-326acba5f7e6
- CAD File (S5-A): a5033222-ec3c-4345-b54a-c5fa0de20cc3

Notes:
- DB: yuantus_cleanup_test_1766468424
- Bucket: yuantus-cleanup-test-1766468424

## Additional Verification - CAD 2D Connectors (auto-detect)

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- GStarCAD File: cd5be06c-755e-4072-b53d-ed7016d5b9ee
- ZWCAD File: 38286688-9cee-4968-b052-10ce25d41bee
- Haochen File: f97dea62-8c2d-4d37-9767-d5305487f344
- Zhongwang File: aa0ebbf7-63d6-4a04-8f91-3607ade231ac
- Auto-detect File: 46a7cf35-ebb7-4ed7-aab4-39717a61054b
