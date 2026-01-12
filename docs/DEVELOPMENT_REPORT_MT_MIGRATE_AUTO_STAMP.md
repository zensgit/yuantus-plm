# Development Report: MT Migrate Auto-Stamp

## Summary
- Improved `scripts/mt_migrate.sh` to stamp a known initial revision when databases have tables but no `alembic_version`, then continue the upgrade.
- Ensured `create_all` includes auth tables by importing auth models in `import_all_models`, so auto-stamp + upgrade works for tenant DBs created in dev.

## Changes
- `scripts/mt_migrate.sh`
  - Added `AUTO_STAMP_REVISION` (default `f87ce5711ce1`).
  - When tables exist without `alembic_version`, stamp to the initial revision and proceed with `alembic upgrade`.
- `src/yuantus/meta_engine/bootstrap.py`
  - Import `yuantus.security.auth.models` to include auth tables in `create_all`.
- `docs/VERIFICATION.md`
  - Documented `AUTO_STAMP_REVISION` usage.

## Verification
- Script: `scripts/mt_migrate.sh`
- Test DB: `yuantus_mt_pg__tenant-stamp2__org-stamp2` (created via `create_all`, no `alembic_version`).
- Result: `Migrations complete`.
- Evidence: `docs/VERIFICATION_RESULTS.md` entry `Run MT-MIGRATE-AUTOSTAMP-20260112-0915`.
