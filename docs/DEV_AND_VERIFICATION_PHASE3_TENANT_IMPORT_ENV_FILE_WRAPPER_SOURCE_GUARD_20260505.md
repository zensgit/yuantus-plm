# Dev & Verification — Phase 3 Tenant Import Env-File Wrapper Source Guard

Date: 2026-05-05

## 1. Summary

Added wrapper-level regression coverage for unsafe P3.4 env files.

The previous safety hardening made `precheck_tenant_import_rehearsal_env_file.sh`
validate repo-external env files before sourcing. This slice pins that behavior
at the two wrapper entrypoints that consume env files:

- command-pack generation;
- full-closeout execution.

No runtime shell logic changed. The tests confirm the current wrappers fail
closed before source-time command execution.

## 2. Files Changed

- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_ENV_FILE_WRAPPER_SOURCE_GUARD_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_FILE_WRAPPER_SOURCE_GUARD_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_FILE_WRAPPER_SOURCE_GUARD_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Test Design

Both wrapper tests create a repo-external env file containing:

```bash
TARGET_DATABASE_URL=$(touch <marker>)
```

The tests then run the wrapper with the unsafe env file and assert:

- return code is `2`;
- stderr reports shell expansion syntax;
- the marker file does not exist;
- no downstream command file or reviewer packet is produced;
- DSN values are not printed.

## 4. Safety Boundaries

This slice does not:

- execute row-copy;
- open a database connection;
- accept evidence;
- change wrapper behavior;
- alter `TENANCY_MODE`;
- change the P3.4 cutover block.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 6. Verification Results

- Focused wrapper/env-file guard suite: 25 passed in 2.07s.
- Combined wrapper/env-file/validator/doc-index suite: 57 passed in 4.00s.
- `git diff --check`: clean.

## 7. Remaining Work

Remaining P3.4 work is still external operator execution:

- real non-production DSNs;
- approved rehearsal window;
- row-copy run;
- real evidence and reviewer packet review.
