# Dev & Verification — Phase 3 Tenant Import Operator Precheck

Date: 2026-04-30

## 1. Summary

Added a DB-free precheck for the P3.4 tenant import rehearsal operator path.

The precheck verifies local prerequisites before the operator executes the real
row-copy rehearsal command sequence. It does not print DSN values or connect to
databases.

## 2. Files Changed

- `scripts/precheck_tenant_import_rehearsal_operator.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_PRECHECK_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_PRECHECK_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_PRECHECK_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The precheck validates:

- implementation packet file exists;
- implementation packet schema version is expected;
- `ready_for_claude_importer=true`;
- `ready_for_cutover=false`;
- implementation packet has no blockers;
- source and target DSN environment variables are set;
- command-printer, launchpack, and evidence-closeout helpers are executable.

## 4. Safety Boundaries

The precheck:

- reports DSN environment variable names only;
- does not print DSN values;
- does not open database connections;
- does not run row-copy rehearsal;
- does not create or accept operator evidence;
- does not build archive or reviewer artifacts;
- keeps cutover authorization out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py

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
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py \
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
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

bash -n scripts/precheck_tenant_import_rehearsal_operator.sh

git diff --check
```

## 6. Verification Results

- Focused operator precheck suite: 5 passed in 0.23s.
- Script syntax and delivery-scripts index contracts: 20 passed in 0.74s.
- Full P3.4 focused suite + doc/script index contracts: 240 passed, 1 skipped, 1 warning in 3.31s.
- Doc-index trio: 4 passed in 0.03s.
- `bash -n scripts/precheck_tenant_import_rehearsal_operator.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- this precheck only validates prerequisites before execution;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
