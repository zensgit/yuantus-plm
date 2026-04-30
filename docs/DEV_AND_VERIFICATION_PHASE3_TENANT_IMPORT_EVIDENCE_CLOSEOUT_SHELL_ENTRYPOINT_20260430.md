# Dev & Verification — Phase 3 Tenant Import Evidence Closeout Shell Entrypoint

Date: 2026-04-30

## 1. Summary

Added a repo-local shell entrypoint for the DB-free P3.4 evidence closeout chain.

After real operator-run PostgreSQL rehearsal evidence exists and the evidence
gate accepts it, the wrapper builds the archive, runs redaction, validates
handoff, runs intake, and emits the reviewer packet in one command.

## 2. Files Changed

- `scripts/run_tenant_import_evidence_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_EVIDENCE_CLOSEOUT_SHELL_ENTRYPOINT_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_EVIDENCE_CLOSEOUT_SHELL_ENTRYPOINT_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EVIDENCE_CLOSEOUT_SHELL_ENTRYPOINT_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The shell entrypoint is a thin orchestration wrapper around existing Python
modules:

```text
tenant_import_rehearsal_evidence_archive
tenant_import_rehearsal_redaction_guard
tenant_import_rehearsal_evidence_handoff
tenant_import_rehearsal_evidence_intake
tenant_import_rehearsal_reviewer_packet
```

It extracts the redaction scan list from the generated archive manifest. This
preserves the existing handoff guarantee that every archived artifact has
redaction coverage.

## 4. Safety Boundaries

The wrapper:

- reads local JSON/Markdown artifacts only;
- writes local JSON/Markdown closeout artifacts only;
- does not expand database URL secret values;
- does not open database connections;
- does not run row-copy rehearsal;
- does not create or accept operator evidence;
- does not synthesize real rehearsal evidence;
- keeps cutover authorization out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py \
  src/yuantus/tests/test_tenant_import_rehearsal_reviewer_packet.py

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

bash -n scripts/run_tenant_import_evidence_closeout.sh

git diff --check
```

## 6. Verification Results

- Focused evidence closeout shell suite: 35 passed in 1.16s.
- Script syntax and delivery-scripts index contracts: 20 passed in 0.77s.
- Full P3.4 focused suite + doc/script index contracts: 231 passed, 1 skipped, 1 warning in 3.22s.
- Doc-index trio: 4 passed in 0.05s.
- `bash -n scripts/run_tenant_import_evidence_closeout.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- this wrapper only accelerates closeout after that evidence exists;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
