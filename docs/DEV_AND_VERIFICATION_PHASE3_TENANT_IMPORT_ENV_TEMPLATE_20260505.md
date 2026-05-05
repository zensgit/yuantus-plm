# Dev & Verification — Phase 3 Tenant Import Env Template

Date: 2026-05-05

## 1. Summary

Added `scripts/generate_tenant_import_rehearsal_env_template.sh`.

The helper generates a repo-external env-file template for the P3.4
full-closeout wrapper's `--env-file` option. It standardizes the operator's
local setup step without requiring real database credentials during development.

## 2. Files Changed

- `scripts/generate_tenant_import_rehearsal_env_template.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_ENV_TEMPLATE_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_TEMPLATE_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_TEMPLATE_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The script writes:

```bash
SOURCE_DATABASE_URL='postgresql://source-user:REPLACE_ME@source-host/source-db'
TARGET_DATABASE_URL='postgresql://target-user:REPLACE_ME@target-host/target-db'
```

The default destination is `$HOME/.config/yuantus/tenant-import-rehearsal.env`.
The file is written with mode 0600, and existing files are protected unless the
operator passes `--force`.

## 4. Safety Boundaries

The script:

- generates placeholders only;
- does not print database URL values;
- refuses accidental overwrite by default;
- does not connect to any database;
- does not run row-copy;
- does not authorize cutover.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_template_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

bash -n scripts/generate_tenant_import_rehearsal_env_template.sh
git diff --check
```

## 6. Verification Results

- Focused env-template shell suite: 5 passed in 0.06s.
- Env-template + full-closeout + script/doc index contracts: 35 passed in
  3.00s.
- `bash -n scripts/generate_tenant_import_rehearsal_env_template.sh`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution is still required:

- fill the generated template with real non-production DSNs;
- run the full-closeout wrapper during the rehearsal window;
- review the generated reviewer packet.
