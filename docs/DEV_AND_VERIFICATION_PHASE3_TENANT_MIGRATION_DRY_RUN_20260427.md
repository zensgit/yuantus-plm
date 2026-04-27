# DEV & Verification — Phase 3 Tenant Migration Dry-Run

Date: 2026-04-27

## 1. Goal

Deliver P3.4.1 read-only migration dry-run tooling. This is preparation for
P3.4 data migration, not the migration itself.

## 2. Delivered

- `src/yuantus/scripts/tenant_migration_dry_run.py`
- `src/yuantus/tests/test_tenant_migration_dry_run.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_MIGRATION_DRY_RUN_20260427.md`
- `docs/PHASE3_TENANT_MIGRATION_DRY_RUN_TODO_20260427.md`
- Runbook and delivery index updates

## 3. Design

The dry-run inspects one source DB and produces JSON/Markdown reports with:

- redacted source URL;
- target schema resolved from the tenant id;
- current global/control-plane table list;
- FK-safe tenant import order;
- source table list;
- row counts for present tenant tables;
- missing tenant tables;
- excluded global tables present in the source;
- unknown source tables;
- readiness and blockers.

The import order uses the same cross-schema FK stripping semantics as the
P3.3.3 tenant baseline generator before sorting tables.

## 4. Scope Controls

- No target DSN is accepted.
- No schema is created.
- No rows are exported or imported.
- No runtime setting is changed.
- `TENANCY_MODE=schema-per-tenant` remains disabled unless a later cutover
  explicitly changes it.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/tests/test_tenant_table_classification_contracts.py \
  src/yuantus/tests/test_tenant_alembic_env.py \
  src/yuantus/tests/test_tenant_baseline_revision.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python scripts/generate_tenant_baseline.py --check
PYTHONPATH=src .venv/bin/python -c "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"
git diff --check
```

Result:

```text
focused pytest: 42 passed, 1 skipped, 1 warning in 2.60s
doc/runbook index: 9 passed in 0.05s
py_compile: passed
generator --check: ok: committed revision matches generator output
boot: routes=672 middleware=4
git diff --check: clean
```

## 6. Next Step

P3.4.2 import rehearsal still requires the external stop-gate inputs:

- named pilot tenant;
- non-production PostgreSQL DSN;
- backup/restore owner;
- rehearsal window;
- signed-off table classification artifact.
