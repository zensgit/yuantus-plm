# Dev & Verification — Phase 3 Tenant Import Full Closeout

Date: 2026-05-05

## 1. Summary

Added a full-closeout operator wrapper for P3.4 tenant import rehearsal.

The wrapper runs the existing operator sequence and evidence closeout wrappers
behind one explicit command with two confirmation flags.

## 2. Files Changed

- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `scripts/run_tenant_import_evidence_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The wrapper executes:

1. `run_tenant_import_rehearsal_operator_sequence.sh`
2. `run_tenant_import_evidence_closeout.sh`

It reduces operator command count while keeping rehearsal execution and
evidence closeout explicit through separate confirmation flags.

## 4. Safety Boundaries

The wrapper:

- requires `--confirm-rehearsal`;
- requires `--confirm-closeout`;
- reads source/target database URLs from environment variables;
- does not print database URL values;
- does not authorize production cutover;
- does not enable runtime schema-per-tenant mode.

## 5. Verification Commands

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

## 6. Verification Results

- Focused full-closeout shell suite: 5 passed in 3.58s.
- Full closeout + operator sequence + evidence closeout + script/doc index
  contracts: 38 passed in 2.73s.
- `bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh`: passed.
- `bash -n scripts/run_tenant_import_evidence_closeout.sh`: passed.
- `git diff --check`: clean.

## 6.1 Follow-Up Fix

The full-closeout test exposed an existing shell edge in
`run_tenant_import_evidence_closeout.sh`: with macOS bash and `set -u`, an empty
archive artifact list caused empty-array expansion to fail before the redaction
guard step. The fix guards the artifact loop with a length check.

## 7. Remaining Work

External operator execution is still required:

- real non-production PostgreSQL source/target DSNs;
- rehearsal window;
- operator-run wrapper execution;
- reviewer inspection of the generated reviewer packet.
