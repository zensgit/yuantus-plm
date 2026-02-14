# Dev & Verification Report - Identity-only Migrations (2026-02-14)

This delivery adds a true split-database migration path for the Identity DB (auth + audit only), without changing the existing `yuantus db upgrade --identity` behavior.

## Changes

### 1) New identity-only Alembic environment

- New: `alembic.identity.ini`
  - `script_location=migrations_identity`
- New: `migrations_identity/`
  - Identity-only Alembic env + initial revision creating:
    - `auth_*` tables
    - `audit_logs`

### 2) CLI support

- `src/yuantus/cli.py`
  - Add `yuantus db ... --identity-only`:
    - Targets `YUANTUS_IDENTITY_DATABASE_URL` (fallback: `YUANTUS_DATABASE_URL`)
    - Uses `alembic.identity.ini` (identity-only schema)

### 3) Evidence-grade verification script + optional suite wiring

- New: `scripts/verify_identity_only_migrations.sh`
  - Creates fresh core + identity SQLite DBs under `/tmp`
  - Runs:
    - core migrations via `alembic.ini`
    - identity-only migrations via `alembic.identity.ini`
  - Asserts identity DB does not contain core tables like `meta_items`
- `scripts/verify_all.sh`
  - Add optional suite `RUN_IDENTITY_ONLY_MIGRATIONS_E2E=1` → `Identity-only Migrations (E2E)`.

## Verification (Executed)

```bash
bash scripts/verify_identity_only_migrations.sh
```

Evidence (referenced in `docs/VERIFICATION_RESULTS.md`):

- Log: `tmp/verify_identity_only_migrations_20260214-164518.log`
- Payloads: `tmp/verify-identity-only-migrations/20260214-164518/`

