# Development Task — Phase 3 Tenant Import URL Env Name Allowlist

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant-import operator shell path so custom
`--source-url-env` and `--target-url-env` values are rejected unless they are
uppercase shell environment variable names.

The accepted pattern is:

```text
^[A-Z_][A-Z0-9_]*$
```

## 2. Reason

The operator wrappers use source/target URL variable names in three sensitive
places:

- env-file precheck before shell source;
- generated command text;
- indirect shell expansion before the real row-copy wrapper.

Rejecting unsafe names before those boundaries prevents spaces, punctuation,
shell metacharacters, lowercase drift, and command-substitution shaped input
from entering the operator command path.

## 3. Scope

Update these shell entrypoints:

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `scripts/precheck_tenant_import_rehearsal_operator.sh`
- `scripts/print_tenant_import_rehearsal_commands.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `scripts/run_tenant_import_operator_launchpack.sh`
- `scripts/run_tenant_import_rehearsal_operator_sequence.sh`
- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`

Update the focused shell contracts and stop-gate documentation contracts.

## 4. Non-Goals

Do not:

- add operator-run PostgreSQL rehearsal evidence;
- connect to any database;
- run row-copy;
- mark P3.4 complete;
- enable runtime `TENANCY_MODE=schema-per-tenant`;
- change Python row-copy behavior;
- narrow custom env names to only the default `SOURCE_DATABASE_URL` and
  `TARGET_DATABASE_URL`.

## 5. Compatibility Decision

Keep existing custom uppercase variable names supported, including
`SRC_DB_URL`, `TGT_DB_URL`, `TENANT_SOURCE_URL`, and `TENANT_TARGET_URL`.

This matches existing Python operator-packet validation, which already requires
uppercase shell environment variable names.

## 6. Required Tests

Focused tests must prove invalid names fail:

- before env files are sourced;
- before `${!name}` indirect expansion;
- before Python launchpack invocation;
- before command files are written;
- inside the command-file validator when validating externally supplied command
  files.

## 7. Verification

Run:

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
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py
```
