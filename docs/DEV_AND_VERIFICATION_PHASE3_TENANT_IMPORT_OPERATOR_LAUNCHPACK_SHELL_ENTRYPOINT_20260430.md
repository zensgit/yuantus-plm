# Dev & Verification — Phase 3 Tenant Import Operator Launchpack Shell Entrypoint

Date: 2026-04-30

## 1. Summary

Added a repo-local shell entrypoint for the DB-free tenant import operator
launchpack.

The wrapper reduces operator command length while preserving the existing Python
module as the only implementation owner.

## 2. Files Changed

- `scripts/run_tenant_import_operator_launchpack.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_LAUNCHPACK_SHELL_ENTRYPOINT_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_LAUNCHPACK_SHELL_ENTRYPOINT_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_LAUNCHPACK_SHELL_ENTRYPOINT_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The shell entrypoint is a thin wrapper around:

```bash
python -m yuantus.scripts.tenant_import_rehearsal_operator_launchpack
```

It derives default output paths from `--artifact-prefix` and passes the full
argument set to the Python module. The wrapper is strict by default so a blocked
launchpack exits non-zero unless the operator explicitly passes `--no-strict`.

## 4. Safety Boundaries

The wrapper:

- reads local JSON artifacts only;
- writes local JSON/Markdown artifacts only;
- does not expand `SOURCE_DATABASE_URL` or `TARGET_DATABASE_URL`;
- does not open database connections;
- does not run row-copy rehearsal;
- does not accept evidence;
- does not build an evidence archive;
- keeps cutover authorization out of scope.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
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
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
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

bash -n scripts/run_tenant_import_operator_launchpack.sh

git diff --check
```

## 6. Verification Results

- Focused shell entrypoint suite: 15 passed in 0.46s.
- Delivery scripts index contract: 2 passed in 0.27s.
- Full P3.4 focused suite + doc/script index contracts: 227 passed, 1 skipped, 1 warning in 2.40s.
- Doc-index trio: 4 passed in 0.03s.
- `bash -n scripts/run_tenant_import_operator_launchpack.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The external blocker is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- evidence intake and archive remain blocked until that rehearsal is run;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
