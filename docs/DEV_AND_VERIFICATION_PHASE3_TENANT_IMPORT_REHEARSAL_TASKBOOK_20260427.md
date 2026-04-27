# DEV & Verification — Phase 3 Tenant Import Rehearsal Taskbook

Date: 2026-04-27

## 1. Goal

Add a design-only taskbook for P3.4.2 tenant import rehearsal.

The intent is to make the future Claude implementation decision-complete while
keeping the current repo safe: no importer code, no database writes, no runtime
cutover, and no production enablement.

## 2. Delivered

- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REHEARSAL_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_REHEARSAL_TASKBOOK_20260427.md`
- `docs/DELIVERY_DOC_INDEX.md` entries

## 3. Design

The taskbook requires the future implementation to:

- consume a P3.4.1 dry-run JSON report;
- require explicit `--confirm-rehearsal`;
- validate `ready_for_import=true`;
- validate target PostgreSQL schema and `alembic_version`;
- import only tenant application tables in dry-run import order;
- keep global/control-plane tables excluded;
- produce JSON/Markdown rehearsal reports;
- keep `ready_for_cutover=false`.

The taskbook blocks implementation until the operator supplies the pilot
tenant, non-production PostgreSQL DSN, backup/restore owner, rehearsal window,
classification sign-off, and a green dry-run report.

## 4. Scope Controls

This PR is documentation-only.

It does not add `tenant_import_rehearsal.py`.

It does not update runtime settings, Alembic revisions, or migration helpers.

It does not write to any database.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

Result:

```text
doc-index focused: 4 passed in 0.03s
git diff --check: clean
```

## 6. Next Step

Do not implement P3.4.2 until the stop gate in
`docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md` is satisfied.
