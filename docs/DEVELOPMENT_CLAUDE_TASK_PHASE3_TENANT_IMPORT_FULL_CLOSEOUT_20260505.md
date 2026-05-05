# Development Task — Phase 3 Tenant Import Full Closeout

Date: 2026-05-05

## 1. Goal

Add a single explicit operator wrapper that runs the P3.4 rehearsal sequence and
then evidence closeout.

## 2. Required Output

- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `docs/PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_20260505.md`
- runbook, script index, and doc index updates

## 3. Safety Contract

The wrapper must:

- require `--confirm-rehearsal`;
- require `--confirm-closeout`;
- use source/target database URLs from environment variables only;
- never print database URL values;
- preserve `Ready for cutover: false`;
- call the existing operator sequence wrapper before evidence closeout;
- not enable runtime schema-per-tenant mode.

## 4. Non-Goals

- No production database import.
- No production cutover authorization.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No automatic rollback or destructive cleanup.

## 5. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh
git diff --check
```
