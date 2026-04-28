# Claude Task — Phase 3 Tenant Import Next-Action Gate

Date: 2026-04-28

## 1. Goal

Add a machine-checkable next-action report for P3.4.2 tenant import rehearsal.

The report answers:

```text
What should happen next, and do we need Claude to implement the importer now?
```

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_next_action`.
- Consume optional P3.4.1 dry-run, P3.4.2 readiness, and Claude handoff JSON
  reports.
- Emit JSON and Markdown next-action reports.
- Set `claude_required=true` only when the handoff is green.
- Return 1 in `--strict` mode until Claude is required.

## 3. Non-Goals

- No importer implementation.
- No database connections.
- No source or target writes.
- No schema creation, migration, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_next_action \
  --dry-run-json output/tenant_<tenant-id>_dry_run.json \
  --readiness-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --handoff-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_next_action.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_next_action.md \
  --strict
```

## 5. Next-Action States

- `run_p3_4_1_dry_run`
- `fix_dry_run_report`
- `fix_dry_run_blockers`
- `collect_stop_gate_inputs_and_run_readiness`
- `fix_readiness_report`
- `fix_readiness_blockers`
- `run_claude_handoff`
- `fix_claude_handoff_report`
- `fix_claude_handoff_blockers`
- `ask_claude_to_implement_importer`

Only the final state sets `claude_required=true`.

## 6. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py

git diff --check
```
