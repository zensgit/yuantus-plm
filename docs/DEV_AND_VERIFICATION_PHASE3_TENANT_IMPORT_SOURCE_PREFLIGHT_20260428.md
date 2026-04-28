# Development & Verification - Phase 3 Tenant Import Source Preflight

Date: 2026-04-28

## 1. Summary

Implemented a P3.4.2 source preflight gate for tenant import rehearsal.

The new gate is read-only and validates source table/column compatibility after
the import plan is green and before target preflight / Claude importer work.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_source_preflight.py`
- `src/yuantus/scripts/tenant_import_rehearsal_next_action.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_next_action.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_SOURCE_PREFLIGHT_20260428.md`
- `docs/PHASE3_TENANT_IMPORT_SOURCE_PREFLIGHT_TODO_20260428.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SOURCE_PREFLIGHT_20260428.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Runtime Boundary

This PR does not implement the importer.

The new script connects only when:

- `--confirm-source-preflight` is present;
- the import plan JSON is valid and green;
- the source URL is present.

All fail-closed cases return a report before opening any DB connection.

## 4. Source Checks

`ready_for_importer_source=true` requires:

- every planned tenant table exists in the source DB;
- every target metadata column exists in the matching source table.

Extra source columns are reported but do not block, because the future importer
can ignore unplanned columns.

`ready_for_cutover=false` remains pinned.

## 5. Next-Action Change

`tenant_import_rehearsal_next_action` now requires the source preflight report
after the import plan and before the target preflight report.

New states:

- `run_source_preflight`
- `fix_source_preflight_report`
- `fix_source_preflight_blockers`

Claude is required only after dry-run, readiness, handoff, plan, source
preflight, and target preflight are all green.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
source-preflight/target-preflight/next-action/plan/handoff/readiness/dry-run/doc-index: 69 passed, 1 skipped, 1 warning in 0.79s
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py
```

Result:

```text
runbook/index contracts: 5 passed in 0.03s
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_source_preflight.py \
  src/yuantus/scripts/tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py
```

Result:

```text
passed
```

```bash
git diff --check
```

Result:

```text
clean
```

## 7. Review Checklist

- Confirm no source row reads were added.
- Confirm no DDL/DML appears in the source preflight implementation.
- Confirm the script cannot connect without `--confirm-source-preflight`.
- Confirm blocked plans fail before `create_engine`.
- Confirm next-action no longer sets `claude_required=true` with only green
  plan and target preflight.
