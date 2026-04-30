# Dev & Verification — Phase 3 Tenant Import Operator Flow

Date: 2026-04-30

## 1. Summary

Added a DB-free operator flow command for P3.4 tenant import rehearsal.

The flow converts an operator execution packet into the three operator-facing
handoff layers in one command:

```text
external status -> operator request -> operator bundle
```

It writes all six downstream JSON/Markdown artifacts plus a summary report. It
does not run the rehearsal command or connect to any database.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_operator_flow.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_flow.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_FLOW_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_FLOW_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_FLOW_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The flow intentionally composes existing builders instead of duplicating their
validation rules. The operator packet remains the root input; the generated
operator bundle Markdown remains the execution handoff.

## 4. Safety Boundaries

The flow:

- reads local JSON only;
- writes local JSON/Markdown only;
- does not run commands;
- does not open database connections;
- does not import the row-copy script;
- does not accept evidence;
- does not build archive or handoff artifacts;
- keeps `ready_for_cutover=false`.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_flow.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_bundle.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_bundle.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_flow.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py \
  src/yuantus/tests/test_tenant_import_rehearsal_reviewer_packet.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_operator_flow.py

git diff --check
```

## 6. Verification Results

- Focused operator flow suite: 33 passed in 0.27s.
- Full P3.4 focused suite + doc-index trio: 198 passed, 1 skipped, 1 warning in 1.38s.
- Doc-index trio: 4 passed in 0.03s.
- `py_compile`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
