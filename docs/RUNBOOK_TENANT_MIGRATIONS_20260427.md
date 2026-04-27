# Runbook — Tenant Schema Provisioning and Migration (2026-04-27)

## 1. Scope

This runbook covers operator actions for schema-per-tenant preparation, post P3.3.3 baseline revision:

- Resolve the managed schema name for a tenant id.
- Provision the tenant schema out of band.
- Generate tenant Alembic offline SQL for review.
- Apply the tenant Alembic baseline revision so tenant application tables exist inside the target schema.

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

Post-P3.3.3, this SQL contains the actual `CREATE TABLE` baseline DDL for tenant application tables. The reviewer must confirm the absence of any `auth_*`, `audit_logs`, `rbac_*`, and `users` table DDL — those tables remain on the global identity plane and must not appear here.

## 6. Apply Baseline Upgrade

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  upgrade head
```

Expected behavior post-P3.3.3: the command applies the baseline revision (`t1_initial_tenant_baseline`) inside `<schema>`, creating tenant application tables and the per-tenant `<schema>.alembic_version` row. Cross-schema FKs to global tables (e.g., `rbac_users`, `users`) are intentionally NOT created — tenant tables retain user-attribution columns (`created_by_id`, `owner_id`, etc.) without a database-level FK constraint, since the referenced rows live in the global identity plane.

## 7. Smoke

Confirm the schema exists, that the baseline revision is recorded, and that representative tenant tables are present:

```sql
select nspname from pg_namespace where nspname = '<schema>';

select version_num from "<schema>"."alembic_version";
-- expect: t1_initial_tenant_baseline

select count(*) from information_schema.tables
where table_schema = '<schema>' and table_name in ('meta_items', 'meta_files', 'meta_conversion_jobs');
-- expect: 3

-- Negative smoke: no global tables in the tenant schema
select count(*) from information_schema.tables
where table_schema = '<schema>'
  and table_name in ('auth_users', 'rbac_users', 'users', 'audit_logs');
-- expect: 0
```

## 8. Rollback

This runbook performs no data migration; rollback is purely schema-level.

For per-schema rollback, use Alembic downgrade explicitly scoped to the target schema:

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  downgrade base
```

Downgrading the baseline (`t1_initial_tenant_baseline`) drops tenant application tables in reverse dependency order. The schema itself is left in place — schema removal is a separate operator action and is not exposed by this runbook.

Never run downgrade without `-x target_schema=<schema>`.

## 9. Stop Gate

Do not start P3.4 cutover (data migration / runtime enablement) until all are true:

- A named pilot tenant exists.
- Non-production rehearsal DB is available.
- Backup/restore owner is named.
- Rehearsal window is scheduled.
- P3.3.1, P3.3.2, and P3.3.3 are merged and smoke green.
- Table classification artifact is signed off.
