# Dev & Verification — Phase 3 Tenant Import Env File Precheck

Date: 2026-05-05

## 1. Summary

Added `scripts/precheck_tenant_import_rehearsal_env_file.sh` and wired it into
the P3.4 full-closeout wrapper.

This prevents placeholder or missing source/target DSN values from reaching the
real row-copy command while staying DB-free and non-secret-printing.

## 2. Files Changed

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The precheck can load `--env-file PATH` or inspect inherited environment
variables. It validates the configured source and target variable names without
printing their values.

The full-closeout wrapper calls the precheck before invoking the operator
sequence wrapper. If the env file still contains generated template placeholders,
execution fails before any database connection attempt.

## 4. Safety Boundaries

The change:

- does not connect to databases;
- does not run row-copy;
- does not print database URL values;
- preserves both full-closeout confirmation gates;
- preserves `Ready for cutover: false`;
- does not enable runtime schema-per-tenant mode.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/precheck_tenant_import_rehearsal_env_file.sh
bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh
git diff --check
```

## 6. Verification Results

- Focused env-file precheck shell suite: 8 passed in 0.05s.
- Full-closeout shell regression: 6 passed in 1.68s.
- Env-file precheck + env-template + full-closeout + script/doc index
  contracts: 43 passed in 2.40s.
- `bash -n scripts/precheck_tenant_import_rehearsal_env_file.sh`: passed.
- `bash -n scripts/run_tenant_import_rehearsal_full_closeout.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution is still required:

- fill the repo-external env file with real non-production DSNs;
- run the full-closeout wrapper during the rehearsal window;
- review the generated reviewer packet.
