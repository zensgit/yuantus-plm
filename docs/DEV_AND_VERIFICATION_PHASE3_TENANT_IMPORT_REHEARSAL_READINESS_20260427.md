# DEV & Verification — Phase 3 Tenant Import Rehearsal Readiness

Date: 2026-04-27

## 1. Goal

Add a safe P3.4.2 readiness validator that can run before any import
rehearsal implementation. It checks external stop-gate inputs and a P3.4.1
dry-run report without opening database connections.

## 2. Delivered

- `src/yuantus/scripts/tenant_import_rehearsal_readiness.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_readiness.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REHEARSAL_READINESS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_READINESS_TODO_20260427.md`
- Runbook and delivery index updates

## 3. Design

The validator consumes CLI stop-gate arguments plus a P3.4.1 dry-run JSON
report. It intentionally avoids a separate intake-file format so operators can
run one command from the runbook.

It emits:

- JSON readiness report;
- Markdown readiness report;
- blockers list;
- redacted non-production PostgreSQL target URL.

Readiness is true only when all stop-gate fields are present, classification is
signed off, the target URL is PostgreSQL-shaped, and the dry-run report is green and
matches the pilot tenant/target schema.

## 4. Scope Controls

- No database connection is opened.
- No source or target database is mutated.
- No importer is added.
- No runtime setting is changed.
- No production cutover is authorized.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py

git diff --check
```

Result:

```text
focused pytest: 19 passed, 1 warning in 0.89s
doc/runbook index: 5 passed in 0.03s
py_compile: passed
git diff --check: clean
```

## 6. Next Step

The actual P3.4.2 importer remains blocked until a readiness report has
`ready_for_import_rehearsal=true`.
