# DEV & Verification — Phase 3 Tenant Import Rehearsal Handoff

Date: 2026-04-28

## 1. Goal

Create a machine-checkable handoff gate for Claude before actual P3.4.2 tenant
import rehearsal implementation starts.

This answers "when can Claude develop?" with an artifact:

```text
ready_for_claude=true
```

The value is derived from the readiness report and cannot be set manually in
chat.

## 2. Delivered

- `src/yuantus/scripts/tenant_import_rehearsal_handoff.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_handoff.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_REHEARSAL_HANDOFF_20260428.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_HANDOFF_TODO_20260428.md`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The handoff generator consumes the P3.4.2 readiness JSON produced by
`tenant_import_rehearsal_readiness`.

It emits:

- JSON handoff report;
- Markdown Claude task handoff;
- blockers list;
- `ready_for_claude`.

The generator returns 1 in `--strict` mode when the readiness report is not
green. This lets operators wire it into an automated pre-implementation gate.

## 4. Claude Start Criteria

Claude can start the actual importer only when all are true:

- readiness schema is `p3.4.2-import-rehearsal-readiness-v1`;
- dry-run schema is `p3.4.1-dry-run-v1`;
- `ready_for_import=true`;
- `ready_for_rehearsal=true`;
- readiness blockers are empty;
- tenant id, target schema, redacted target URL, and dry-run JSON are present.

## 5. Scope Controls

- No importer implementation.
- No DB connection.
- No source or target mutation.
- No schema create/drop/migration.
- No runtime setting change.
- No production cutover.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py

git diff --check
```

## 7. Results

```text
handoff/readiness/dry-run/doc-index: 29 passed, 1 warning in 0.83s
runbook/index contracts: 5 passed in 0.03s
py_compile: passed
git diff --check: clean
```

## 8. Next Step

Do not ask Claude to implement `tenant_import_rehearsal` until a generated
handoff Markdown says:

```text
Claude can start: `true`
```
