# Development Task — Phase 3 Tenant Import Env File Precheck

Date: 2026-05-05

## 1. Goal

Add a DB-free guard that validates P3.4 tenant import rehearsal source and
target database URL variables before the full-closeout wrapper reaches row-copy.

## 2. Required Output

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The precheck validates either inherited environment variables or a supplied
repo-external env file.

It checks:

- source database URL variable is set;
- target database URL variable is set;
- neither value contains placeholder markers;
- both values use a PostgreSQL URL shape.

The full-closeout wrapper invokes this precheck before loading the env file for
the operator sequence, so placeholder templates fail before row-copy can start.

## 4. Safety Contract

The precheck must:

- not connect to either database;
- not run row-copy;
- not print database URL values;
- not enable runtime schema-per-tenant mode;
- keep `Ready for cutover: false`;
- support custom source/target variable names.

## 5. Verification

Run:

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
