# DEV & Verification — Phase 3 Tenant Import Next Action

Date: 2026-04-28

## 1. Goal

Create a status gate that tells the operator what to do next in P3.4.2 and
whether Claude should be asked to implement the actual tenant import rehearsal
importer.

This replaces chat-only judgment with a JSON/Markdown artifact.

## 2. Delivered

- `src/yuantus/scripts/tenant_import_rehearsal_next_action.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_next_action.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_NEXT_ACTION_20260428.md`
- `docs/PHASE3_TENANT_IMPORT_NEXT_ACTION_TODO_20260428.md`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The next-action command reads up to five reports:

- P3.4.1 dry-run JSON;
- P3.4.2 readiness JSON;
- Claude handoff JSON;
- import rehearsal plan JSON;
- target preflight JSON.

It emits:

- `next_action`;
- `claude_required`;
- context fields for tenant/schema/report paths;
- blockers.

`claude_required=true` only when the handoff, plan, and target preflight
reports are green and the next action is `ask_claude_to_implement_importer`.

## 4. Scope Controls

- No DB connection.
- No source or target mutation.
- No importer implementation.
- No schema create/drop/migration.
- No runtime setting change.
- No production cutover.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
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
  src/yuantus/scripts/tenant_import_rehearsal_target_preflight.py \
  src/yuantus/scripts/tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py

git diff --check
```

## 6. Results

```text
next-action/handoff/readiness/dry-run/doc-index: 38 passed, 1 warning in 0.77s
runbook/index contracts: 5 passed in 0.03s
py_compile: passed
git diff --check: clean
```

## 7. Claude Notification Rule

Tell the user "now let Claude implement the importer" only when the report says:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```
