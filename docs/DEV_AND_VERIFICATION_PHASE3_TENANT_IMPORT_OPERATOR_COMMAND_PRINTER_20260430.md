# Dev & Verification — Phase 3 Tenant Import Operator Command Printer

Date: 2026-04-30

## 1. Summary

Added a print-only P3.4 tenant import rehearsal command helper.

The helper prints the operator command sequence from implementation packet
through evidence closeout. It does not execute commands, read DSN values, or
authorize cutover.

## 2. Files Changed

- `scripts/print_tenant_import_rehearsal_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PRINTER_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PRINTER_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_COMMAND_PRINTER_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The script prints a deterministic command sequence:

```text
scripts/run_tenant_import_operator_launchpack.sh
python -m yuantus.scripts.tenant_import_rehearsal
python -m yuantus.scripts.tenant_import_rehearsal_evidence_template
python -m yuantus.scripts.tenant_import_rehearsal_evidence
scripts/run_tenant_import_evidence_closeout.sh
```

The row-copy command references DSNs through environment variables such as
`$SOURCE_DATABASE_URL` and `$TARGET_DATABASE_URL`.

## 4. Safety Boundaries

The helper:

- prints commands only;
- does not expand secret DSN values;
- does not open database connections;
- does not run row-copy rehearsal;
- does not create or accept operator evidence;
- does not build archive or reviewer artifacts;
- keeps cutover authorization out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py

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

bash -n scripts/print_tenant_import_rehearsal_commands.sh

git diff --check
```

## 6. Verification Results

- Focused command-printer suite: 4 passed in 0.03s.
- Script syntax and delivery-scripts index contracts: 20 passed in 0.63s.
- Full P3.4 focused suite + doc/script index contracts: 235 passed, 1 skipped, 1 warning in 3.30s.
- Doc-index trio: 4 passed in 0.03s.
- `bash -n scripts/print_tenant_import_rehearsal_commands.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- this helper only prints the command sequence;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
