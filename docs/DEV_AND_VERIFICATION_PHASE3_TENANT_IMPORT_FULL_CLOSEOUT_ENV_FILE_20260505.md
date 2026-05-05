# Dev & Verification — Phase 3 Tenant Import Full Closeout Env File

Date: 2026-05-05

## 1. Summary

Added optional `--env-file` support to the P3.4 full-closeout wrapper.

This lets operators keep source and target database URL values in a local
repo-external file instead of exporting them manually in the shell before every
rehearsal command.

## 2. Files Changed

- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_ENV_FILE_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_ENV_FILE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_FULL_CLOSEOUT_ENV_FILE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The wrapper now accepts:

```bash
--env-file PATH
```

When present, the wrapper verifies the file exists, sources it with automatic
export enabled, and then invokes the existing operator sequence wrapper. The
child wrapper still receives database URLs through environment variables, so no
downstream argument shape changes.

## 4. Safety Boundaries

The change:

- keeps `--env-file` optional;
- preserves the existing direct environment variable path;
- does not print database URL values;
- keeps the env file repo-external in runbook guidance;
- preserves `--confirm-rehearsal`;
- preserves `--confirm-closeout`;
- preserves `Ready for cutover: false`.

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

- Focused full-closeout shell suite: 6 passed in 1.69s.
- Full closeout + operator sequence + evidence closeout + script/doc index
  contracts: 39 passed in 3.18s.
- `bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution is still required:

- real non-production PostgreSQL source/target DSNs;
- repo-external env file creation by the operator;
- rehearsal window;
- operator-run wrapper execution;
- reviewer inspection of the generated reviewer packet.
