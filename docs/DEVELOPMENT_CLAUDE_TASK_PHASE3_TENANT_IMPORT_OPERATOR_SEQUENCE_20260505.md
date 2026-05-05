# Development Task — Phase 3 Tenant Import Operator Sequence

Date: 2026-05-05

## 1. Goal

Add a single explicit operator sequence wrapper for P3.4 rehearsal execution.

The wrapper should reduce operator command count by chaining precheck,
launchpack, real row-copy rehearsal, operator evidence template generation, and
evidence precheck.

## 2. Required Output

- `scripts/run_tenant_import_rehearsal_operator_sequence.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_SEQUENCE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_SEQUENCE_20260505.md`
- runbook, script index, and doc index updates

## 3. Safety Contract

The wrapper must:

- require `--confirm-rehearsal`;
- use source/target database URLs from environment variables only;
- never print database URL values;
- run only against the existing non-production rehearsal path;
- keep `Ready for cutover: false`;
- stop before archive, handoff, intake, reviewer packet, and production cutover.

## 4. Non-Goals

- No production database import.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No evidence closeout archive generation.
- No reviewer-packet generation.
- No automatic rollback or destructive cleanup.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_precheck_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/run_tenant_import_rehearsal_operator_sequence.sh
git diff --check
```
