# Development and Verification Report (2026-02-03)

## Summary
- Aligned regression scripts with server runtime configuration (env + storage) to avoid mismatched DB/storage paths.
- Fixed Alembic baseline migration for Postgres when adding columns without batch ops.
- Corrected MBOM conversion DB resolution for db-per-tenant and db-per-tenant-org modes.

## Changes
- `scripts/verify_all.sh`: load `.env` YUANTUS_* defaults, read storage settings from `/api/v1/health/deps`, and avoid forcing MinIO S3 when server is local storage.
- `migrations/versions/u1b2c3d4e6a9_add_baseline_reports.py`: ensure `op.add_column` receives table name when not using `batch_alter_table`.
- `scripts/verify_mbom_convert.sh`: resolve per-tenant DB URL even when `DB_URL_TEMPLATE` is not provided.
- `docs/VERIFICATION_RESULTS.md`: added latest verify_all runs.

## Verification
1) Core regression (db-per-tenant-org, default options)
- Command: `MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_1545.log`
- Result: PASS (PASS: 35 / FAIL: 0 / SKIP: 18)

2) Extended regression (UI aggregation + Ops S8 enabled)
- Command: `RUN_UI_AGG=1 RUN_OPS_S8=1 MIGRATE_TENANT_DB=1 ./scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_20260203_154533.log`
- Result: PASS (PASS: 41 / FAIL: 0 / SKIP: 12)
- Note: Ops S8 skipped because audit is disabled.

## Notes
- Warnings about missing `cadquery` and Elasticsearch library are expected in this environment; all tests still passed.
