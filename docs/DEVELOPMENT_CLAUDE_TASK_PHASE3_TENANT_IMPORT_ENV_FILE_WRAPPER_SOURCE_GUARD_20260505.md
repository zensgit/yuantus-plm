# Development Task — Phase 3 Tenant Import Env-File Wrapper Source Guard

Date: 2026-05-05

## 1. Goal

Pin the wrapper-level safety contract for repo-external P3.4 env files.

The env-file precheck already rejects unsafe shell syntax before sourcing. This
task adds explicit wrapper-level regression coverage proving the two env-file
consumers also fail closed before command execution:

- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `scripts/run_tenant_import_rehearsal_full_closeout.sh`

## 2. Scope

This is a behavior-contract hardening slice.

Modify:

- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- delivery documentation index

Add:

- this development task
- TODO record
- development and verification record

## 3. Required Behavior

If an env file contains command substitution or another unsafe shell expansion:

- the wrapper must exit non-zero;
- the command substitution must not execute;
- no generated command file or reviewer packet should be produced;
- stdout/stderr must not expose DSN values.

## 4. Non-Goals

Do not:

- connect to a source or target database;
- run row-copy;
- accept operator evidence;
- change shell wrapper runtime behavior unless the new tests expose a defect;
- alter `TENANCY_MODE`;
- authorize cutover.

## 5. Verification

Run:

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

## 6. Exit Criteria

- Wrapper-level unsafe env-file tests pass.
- Existing env-file precheck tests still pass.
- Doc-index contracts pass after documentation is indexed.
- P3.4 external stop gate remains unchanged.
