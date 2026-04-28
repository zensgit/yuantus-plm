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

## 6. P3.4.1 Read-Only Source Dry Run

Before any import rehearsal, inspect the source database without touching a
target schema:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_migration_dry_run \
  --source-url <source-db-url> \
  --tenant-id <tenant-id> \
  --output-json output/tenant_<tenant-id>_dry_run.json \
  --output-md output/tenant_<tenant-id>_dry_run.md
```

Use `--strict` in CI or rehearsal automation when blockers should fail the
command:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_migration_dry_run \
  --source-url <source-db-url> \
  --tenant-id <tenant-id> \
  --output-json output/tenant_<tenant-id>_dry_run.json \
  --output-md output/tenant_<tenant-id>_dry_run.md \
  --strict
```

The dry-run report includes the FK-safe tenant import order, source table
inventory, tenant-table row counts, missing tenant tables, excluded global
tables, and unknown source tables. It never accepts a target DSN, never creates
schemas, and never exports or imports rows.

Do not proceed to import rehearsal while `ready_for_import` is false.

This dry run does not satisfy the external P3.4 stop-gate items by itself; the
pilot tenant, non-production PostgreSQL DSN, backup/restore owner, rehearsal
window, and classification sign-off are still required.

## 7. P3.4.2 Import Rehearsal Readiness

Before implementing or running import rehearsal tooling, validate the external
stop-gate inputs and P3.4.1 dry-run report without opening database
connections:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_readiness \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --tenant-id <tenant-id> \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --backup-restore-owner <owner> \
  --rehearsal-window <window> \
  --classification-artifact docs/TENANT_TABLE_CLASSIFICATION_20260427.md \
  --classification-signed-off \
  --output-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_readiness.md \
  --strict
```

Do not implement or run import rehearsal while
`ready_for_rehearsal` is false.

The `--classification-signed-off` flag is not sufficient by itself. The
validator also parses `docs/TENANT_TABLE_CLASSIFICATION_20260427.md` §6 and
requires the Sign-Off block to contain non-placeholder values for:

- `Pilot tenant`
- `PostgreSQL rehearsal DSN`
- `Backup/restore owner`
- `Rehearsal window`
- `Reviewer`
- `Decision`
- `Date`

The tracked document must use a redacted PostgreSQL DSN, for example
`postgresql://user:***@host/db`; never put a plaintext password in the
classification artifact. The validator compares this redacted DSN, the pilot
tenant, backup/restore owner, and rehearsal window with the CLI inputs before
setting `ready_for_rehearsal=true`.

## 8. P3.4.2 Claude Implementation Handoff

Claude can start implementing the actual rehearsal importer only after the
readiness report is green and the handoff generator produces a green task
packet:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_handoff \
  --readiness-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --output-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-md output/tenant_<tenant-id>_claude_import_rehearsal_task.md \
  --strict
```

The command must exit 0 and the generated Markdown must say:

```text
Claude can start: `true`
```

If the command exits 1, do not ask Claude to implement
`yuantus.scripts.tenant_import_rehearsal`; resolve the blockers in the handoff
report first.

The handoff generator does not open database connections and does not authorize
production cutover. It only converts verified readiness evidence into a bounded
Claude task packet.

## 9. P3.4.2 Import Rehearsal Plan

Before asking Claude to implement the importer, freeze the table-level plan
derived from the dry-run and handoff artifacts:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_plan \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --handoff-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_plan.md \
  --strict
```

The command must exit 0 and set `ready_for_importer=true`. It does not open
database connections; it pins the import order, source row-count expectations,
and global/control-plane table skip list. `ready_for_cutover` must stay false.

If the command exits 1, do not ask Claude to implement the importer. Fix the
plan blockers first.

## 10. P3.4.2 Source Preflight

Before asking Claude to implement the importer, run a read-only source schema
preflight:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_source_preflight \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --source-url <source-db-url> \
  --output-json output/tenant_<tenant-id>_source_preflight.json \
  --output-md output/tenant_<tenant-id>_source_preflight.md \
  --confirm-source-preflight \
  --strict
```

The command must exit 0 and set `ready_for_importer_source=true`. It validates
that the planned tenant tables exist in the source DB and that required target
metadata columns are present. It does not read rows, export rows, connect to a
target DB, or authorize cutover.

If the command exits 1, do not ask Claude to implement the importer. Fix the
source preflight blockers first.

## 11. Apply Baseline Upgrade

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini \
  -x target_schema=<schema> \
  upgrade head
```

Expected behavior post-P3.3.3: the command applies the baseline revision (`t1_initial_tenant_baseline`) inside `<schema>`, creating tenant application tables and the per-tenant `<schema>.alembic_version` row. Cross-schema FKs to global tables (e.g., `rbac_users`, `users`) are intentionally NOT created — tenant tables retain user-attribution columns (`created_by_id`, `owner_id`, etc.) without a database-level FK constraint, since the referenced rows live in the global identity plane.

## 12. Smoke

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

## 13. P3.4.2 Target Preflight

Before asking Claude to implement the importer, run a read-only target schema
preflight against the non-production PostgreSQL rehearsal database:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_target_preflight \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --target-url <non-prod-postgres-dsn> \
  --target-schema <schema> \
  --output-json output/tenant_<tenant-id>_target_preflight.json \
  --output-md output/tenant_<tenant-id>_target_preflight.md \
  --confirm-target-preflight \
  --strict
```

The command must exit 0 and set `ready_for_importer_target=true`. It validates
the target schema, `<schema>.alembic_version`, expected tenant table presence,
and the absence of global/control-plane tables. It does not create schemas,
apply migrations, import rows, or authorize cutover.

If the command exits 1, do not ask Claude to implement the importer. Fix the
target preflight blockers first.

## 14. P3.4.2 Next Action / Claude Notification

Use this command when you need a single status artifact that says what to do
next and whether Claude should start implementation:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_next_action \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --readiness-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --handoff-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --plan-json output/tenant_<tenant-id>_import_rehearsal_plan.json \
  --source-preflight-json output/tenant_<tenant-id>_source_preflight.json \
  --target-preflight-json output/tenant_<tenant-id>_target_preflight.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_next_action.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_next_action.md \
  --strict
```

The command returns 0 in `--strict` mode only when the next action is to ask
Claude to implement the importer. Otherwise it writes blockers and returns 1.

Notify the user that Claude development is needed only when the generated
report says:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```

## 15. P3.4.2 Claude Importer Implementation Packet

After next-action is green, generate the final Claude implementation packet:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_implementation_packet \
  --next-action-json output/tenant_<tenant-id>_import_rehearsal_next_action.json \
  --output-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --output-md output/tenant_<tenant-id>_claude_importer_task.md \
  --strict
```

Pass the generated Markdown to Claude only when it says:

```text
Claude can implement importer: `true`
```

The packet generator does not connect to any database and does not authorize
production cutover. It only converts the full green evidence chain into a
bounded implementation task for `yuantus.scripts.tenant_import_rehearsal`.

The packet generator also re-opens every upstream JSON artifact referenced by
next-action and blocks if any file is missing, has the wrong schema version, is
not ready, contains blockers, or disagrees with the next-action tenant/schema
context. Do not hand the Markdown to Claude unless the `Artifact Integrity`
table shows every ready value as `true`.

## 16. P3.4.2 Tenant Import Rehearsal Row Copy

After the implementation packet is green, run the guarded row-copy rehearsal:

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --source-url "$SOURCE_DATABASE_URL" \
  --target-url "$TARGET_DATABASE_URL" \
  --output-json output/tenant_<tenant-id>_import_rehearsal.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal.md \
  --confirm-rehearsal \
  --strict
```

The command revalidates the implementation packet and all upstream JSON
artifacts before opening any database connection. It then copies only the
tenant application tables listed by `tenant_tables_in_import_order` and writes a
JSON/Markdown report with table-level row counts.

Do not treat this as production cutover. The report must say:

```text
Scaffold guard passed: `true`
Rehearsal import passed: `true`
Import executed: `true`
DB connection attempted: `true`
Ready for cutover: `false`
```

The command must not import any global/control-plane table, must not create or
migrate schemas, and must not enable `TENANCY_MODE=schema-per-tenant`.

## 17. Rollback

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

## 18. Stop Gate

Do not start P3.4 cutover (data migration / runtime enablement) until all are true:

- A named pilot tenant exists.
- Non-production rehearsal DB is available.
- Backup/restore owner is named.
- Rehearsal window is scheduled.
- P3.3.1, P3.3.2, and P3.3.3 are merged and smoke green.
- Table classification artifact is signed off.
