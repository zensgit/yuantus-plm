# Runbook — Tenant Schema Provisioning and Migration Wiring (2026-04-27)

## 1. Scope

This runbook covers P3.3.2 operator actions for schema-per-tenant preparation:

- Resolve the managed schema name for a tenant id.
- Provision the tenant schema out of band.
- Generate tenant Alembic offline SQL for review.
- Run a wiring-only tenant Alembic upgrade while `migrations_tenant/versions/` is empty.

This runbook does not authorize runtime cutover, data migration, or production enablement.

## 2. Prerequisites

- P3.3.1 tenant Alembic env is merged.
- `DATABASE_URL` points at a non-production PostgreSQL database for rehearsal.
- `TENANCY_MODE` remains `single` unless a later P3.4 cutover explicitly changes it.
- Operator has an approved tenant id and a named reviewer for offline SQL.

## 3. Resolve Schema

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_schema resolve --tenant-id=<tenant-id>
```

Expected output:

```text
yt_t_<sanitized_tenant>
```

Stop if the output does not match the approved tenant record.

## 4. Provision Schema

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  python -m yuantus.scripts.tenant_schema create --tenant-id=<tenant-id>
```

The helper is idempotent and only issues `CREATE SCHEMA IF NOT EXISTS`.

It does not change privileges, ownership, tenant roles, or runtime settings.

## 5. Generate Offline SQL

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  upgrade head --sql > tenant_<schema>_<timestamp>.sql
```

Reviewer checklist:

- The first non-comment, non-blank SQL line is `SET search_path TO "<schema>", public;`.
- No DDL appears before that `SET search_path` line.
- `alembic_version` is targeted at the tenant schema.
- No global/control-plane table DDL appears for `auth_*`, `audit_logs`, `rbac_*`, or `users`.

Because P3.3.1 intentionally ships with an empty `migrations_tenant/versions/`, this SQL is a wiring review until a tenant baseline revision lands.

## 6. Apply Wiring Upgrade

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  upgrade head
```

Expected P3.3.2 behavior: the command validates env wiring and exits cleanly. It does not create tenant application tables while the tenant versions directory is empty.

## 7. Smoke

Run a read-only check that confirms the schema exists:

```sql
select nspname from pg_namespace where nspname = '<schema>';
```

Do not assert that application tables exist until a tenant baseline revision ships in a later sub-PR.

## 8. Rollback

P3.3.2 has no data rollback because it performs no data migration.

For later tenant revisions, rollback must be explicit and per schema:

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  downgrade <revision>
```

Never run downgrade without `-x target_schema=<schema>`.

## 9. Stop Gate

Do not start P3.4 cutover until all are true:

- A named pilot tenant exists.
- Non-production rehearsal DB is available.
- Backup/restore owner is named.
- Rehearsal window is scheduled.
- P3.3.1 and P3.3.2 are merged and smoke green.
- Table classification artifact is signed off.
