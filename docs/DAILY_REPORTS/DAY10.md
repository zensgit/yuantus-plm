# Day 10 - Multi-Tenant Migrations

## Scope
- Provide a batch migration helper for db-per-tenant-org deployments.

## Changes
- Added `scripts/mt_migrate.sh` with db-per-tenant/org support.
- Added auto-stamp path for existing schemas without `alembic_version`.
- Extended CLI `yuantus db` to support `stamp` action.

## Verification

Command:

```bash
MODE=db-per-tenant-org \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
  ./scripts/mt_migrate.sh
```

Result:

```text
Migrations complete.
```
