# Dev & Verification - Phase 3 Tenant Import Env File Key Allowlist

Date: 2026-05-05

## 1. Summary

Restricted P3.4 tenant import rehearsal env files to only the selected source
and target database URL variable names.

This closes the gap where a static assignment such as `PATH=...` or
`PYTHON=...` could pass the static syntax precheck and then be loaded by the
command-pack or full-closeout wrapper.

## 2. Files Changed

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_ENV_FILE_KEY_ALLOWLIST_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_FILE_KEY_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_FILE_KEY_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

`validate_env_file_static_safety()` now captures the assignment key before any
env-file source operation. The key must equal the selected `source_url_env` or
`target_url_env` value. This keeps custom variable names supported while
blocking unrelated environment mutations.

The validation order is intentionally:

- validate selected variable names;
- parse env-file assignment syntax;
- reject unsupported keys;
- validate value quoting/syntax;
- source the file only after all static checks pass;
- validate source/target URL values without printing them.

## 4. Regression Coverage

The direct precheck tests cover:

- loading custom variable names from an env file;
- rejecting extra static keys before source;
- rejecting default names when custom names are selected;
- preserving DSN redaction on failure.

The wrapper tests cover:

- command-pack wrapper refuses unsupported env-file keys before writing a
  command file;
- full-closeout wrapper refuses unsupported env-file keys before creating
  reviewer artifacts.

The stop-gate contracts keep the fix scoped to local safety and preserve the
external operator-run PostgreSQL evidence blocker.

## 5. Verification Commands

```bash
bash -n \
  scripts/precheck_tenant_import_rehearsal_env_file.sh \
  scripts/prepare_tenant_import_rehearsal_operator_commands.sh \
  scripts/run_tenant_import_rehearsal_full_closeout.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 6. Verification Results

- Shell syntax: passed.
- Direct precheck + command-pack + full-closeout shell suites: 33 passed.
- Focused regression with stop-gate and doc-index contracts: 47 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
