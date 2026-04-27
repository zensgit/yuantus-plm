# Claude Task — Phase 3 P3.3.3 Tenant Baseline Revision (2026-04-27)

## 1. Context

Current main is expected to include:

- P3.3.1 tenant Alembic env: `migrations_tenant/`, `alembic_tenant.ini`, `GLOBAL_TABLE_NAMES`, tenant metadata contracts.
- P3.3.2 provisioning helper/runbook: `provision_tenant_schema()`, `resolve/create` CLI, `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.

At this point `migrations_tenant/versions/` is intentionally empty. Tenant Alembic can validate wiring, but it cannot yet create tenant application tables. P3.3.3 is the baseline-revision slice that closes that gap.

## 2. Goal

Create the initial tenant baseline Alembic revision for `migrations_tenant/` so a provisioned tenant schema can be upgraded from empty to the tenant application table set.

After this PR, an operator should be able to run, on a non-production PostgreSQL DB:

```bash
PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  python -m yuantus.scripts.tenant_schema create --tenant-id=<tenant-id>

PYTHONPATH=src YUANTUS_DATABASE_URL=<postgres-dsn> \
  alembic -c alembic_tenant.ini -x target_schema=<schema> upgrade head
```

and then verify that tenant application tables exist inside `<schema>` while global/control-plane tables do not.

## 3. Strict Scope

In scope:

- One initial tenant baseline revision under `migrations_tenant/versions/`.
- Contract tests proving the baseline creates tenant application tables and excludes global tables.
- Offline SQL tests proving the baseline output starts with `SET search_path` and contains no global-table DDL.
- Update `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md` to replace the P3.3.2 “wiring-only” caveat with baseline-ready instructions.
- Add a DEV/verification MD and index entry.

Out of scope:

- No data migration from existing DBs.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No changes to `database.py`, `get_db()`, or runtime request routing.
- No identity/RBAC/user table creation in tenant schemas.
- No tenant role separation, `GRANT`, `REVOKE`, `OWNER TO`, or `DROP SCHEMA` helper.
- No production DB mutation. Any real PostgreSQL integration test must require explicit `YUANTUS_TEST_PG_DSN` and skip otherwise.

## 4. Baseline Revision Requirements

Suggested revision file:

```text
migrations_tenant/versions/t1_initial_tenant_schema.py
```

Requirements:

- `down_revision = None`.
- `upgrade()` creates tenant application tables only.
- `downgrade()` drops those tenant application tables in reverse dependency order.
- No global/control-plane table appears anywhere in the revision:
  - `auth_*`
  - `audit_logs`
  - `rbac_*`
  - `users`
- The revision must not rely on `Base.metadata.create_all()` at runtime. It must be a normal Alembic revision using `op.create_table`, `op.create_index`, and related Alembic operations.
- Preserve foreign-key relationships among tenant application tables.
- If a tenant application table currently has FK columns pointing to global RBAC/users tables, do not create tenant-side global tables. Prefer preserving the column without the cross-schema FK constraint unless a safe same-schema target exists.

## 5. Generation Strategy

Recommended implementation sequence:

1. Use the current `build_tenant_metadata()` as source of truth.
2. Generate the baseline revision from metadata in a deterministic way.
3. Review generated DDL for:
   - table ordering
   - index / unique constraint preservation
   - absence of global table DDL
   - no FK constraints targeting excluded global tables
4. Keep the final revision checked in as a static Alembic revision, not as a generator script.

If autogenerate requires a real PostgreSQL DSN and none is available, do not invent an unreviewed manual mega-revision. Instead, build a small deterministic local generator from SQLAlchemy metadata, commit the generated revision, and add tests that inspect the generated revision and run offline SQL.

## 6. Required Tests

Add tests under `src/yuantus/tests/`, suggested file:

```text
src/yuantus/tests/test_tenant_baseline_revision.py
```

Minimum contracts:

- `migrations_tenant/versions/` contains exactly one baseline revision and no accidental extra revisions.
- Baseline revision has `down_revision = None`.
- Revision source contains no global table names from `GLOBAL_TABLE_NAMES`.
- Offline SQL for `upgrade head --sql`:
  - first non-comment, non-blank line is `SET search_path TO "<schema>", public;`
  - contains tenant application DDL
  - contains no global-table DDL
- Optional real PostgreSQL integration, skipped unless `YUANTUS_TEST_PG_DSN` is set:
  - provision unique tenant schema
  - run `alembic -c alembic_tenant.ini -x target_schema=<schema> upgrade head`
  - assert representative tenant tables exist
  - assert global tables do not exist in the tenant schema
  - assert `<schema>.alembic_version` exists
  - cleanup only the generated unique schema

## 7. Representative Table Assertions

Choose representative tenant tables from actual tenant metadata, not hard-coded guesses. At minimum assert that a few stable application tables exist after upgrade, such as:

- item / relationship core table(s)
- file metadata table(s)
- job / workflow table(s)

Do not assert global/control-plane tables exist.

## 8. Docs To Update

Update:

- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`

Add:

- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_BASELINE_REVISION_20260427.md`

Update:

- `docs/DELIVERY_DOC_INDEX.md`

The DEV/verification MD must record:

- baseline generation method
- table-count summary
- global-table exclusion result
- offline SQL result
- optional PostgreSQL integration result or explicit skip reason
- exact verification commands

## 9. Verification Commands

Run at minimum:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_baseline_revision.py \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_tenant_schema_provision.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  migrations_tenant/env.py \
  src/yuantus/scripts/tenant_schema.py \
  src/yuantus/tests/test_tenant_baseline_revision.py

PYTHONPATH=src .venv/bin/python -c "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 10. PR Shape

Suggested branch:

```text
feat/tenant-baseline-revision-20260427
```

Suggested PR title:

```text
feat: P3.3.3 tenant baseline revision
```

PR should be self-contained and should not include P3.4 data-migration or runtime cutover work.

## 11. Stop Rule

If the baseline revision generation produces ambiguous or unsafe output, stop and report findings instead of force-fitting the revision.

Examples of stop conditions:

- Global/control-plane table DDL appears in tenant SQL.
- Tenant table FKs require excluded global tables in the same schema.
- Alembic offline SQL does not begin with tenant `SET search_path`.
- The generated revision is non-deterministic between runs.
