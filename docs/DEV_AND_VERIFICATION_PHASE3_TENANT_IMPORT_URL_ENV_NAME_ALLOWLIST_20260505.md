# Development and Verification — Phase 3 Tenant Import URL Env Name Allowlist

Date: 2026-05-05

## 1. Summary

This PR hardens the P3.4 tenant-import operator shell path by validating custom
`--source-url-env` and `--target-url-env` names before they reach env-file
source, command generation, indirect shell expansion, or Python launchpack
delegation.

Accepted names must match:

```text
^[A-Z_][A-Z0-9_]*$
```

## 2. Files Changed

Shell helpers:

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `scripts/precheck_tenant_import_rehearsal_operator.sh`
- `scripts/print_tenant_import_rehearsal_commands.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `scripts/run_tenant_import_operator_launchpack.sh`
- `scripts/run_tenant_import_rehearsal_operator_sequence.sh`
- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`

Tests:

- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`

Docs:

- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_URL_ENV_NAME_ALLOWLIST_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_URL_ENV_NAME_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_URL_ENV_NAME_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Development Notes

The shell validation intentionally mirrors the existing Python operator-packet
contract: custom names are allowed, but only uppercase shell environment
variable names are accepted.

The generated command-file validator also checks `--source-url "$NAME"` and
`--target-url "$NAME"` references, so externally supplied command files cannot
bypass the same constraint.

## 4. Preserved Boundaries

This PR does not:

- connect to any database;
- run row-copy;
- add operator-run PostgreSQL rehearsal evidence;
- mark P3.4 complete;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 5. Verification

Shell syntax:

```bash
bash -n \
  scripts/precheck_tenant_import_rehearsal_env_file.sh \
  scripts/precheck_tenant_import_rehearsal_operator.sh \
  scripts/print_tenant_import_rehearsal_commands.sh \
  scripts/prepare_tenant_import_rehearsal_operator_commands.sh \
  scripts/run_tenant_import_operator_launchpack.sh \
  scripts/run_tenant_import_rehearsal_operator_sequence.sh \
  scripts/run_tenant_import_rehearsal_full_closeout.sh \
  scripts/validate_tenant_import_rehearsal_operator_commands.sh
```

Result: passed.

Focused shell/operator suite:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py
```

Result:

```text
67 passed in 3.25s
```

Final focused verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_printer.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_launchpack_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_sequence_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
81 passed in 3.18s
```

Whitespace check:

```bash
git diff --check
```

Result: clean.

## 6. Remaining Work

The external P3.4 operator-run PostgreSQL rehearsal evidence remains missing.
This PR only reduces command-path risk before that operator run.
