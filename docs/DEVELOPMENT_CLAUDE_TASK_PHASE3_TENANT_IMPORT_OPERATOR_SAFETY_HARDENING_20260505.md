# Development Task — Phase 3 Tenant Import Operator Safety Hardening

Date: 2026-05-05

## 1. Goal

Harden the P3.4 operator handoff path without executing any database operation.

This task closes two DB-free safety gaps:

- generated operator command files must preserve the expected command order;
- repo-external env files must be statically safe before they are sourced.

## 2. Scope

Modify only the local safety gates around existing operator tooling:

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- focused shell tests for both scripts
- P3.4 runbook wording
- delivery doc index

## 3. Command-File Validator Requirements

The command-file validator must continue to run without executing the generated
file. It must also assert:

- required operator steps appear in the expected order;
- row-copy uses environment-variable URL references, not literal files or URLs;
- command files do not print env vars through `echo "$..."`, `printf "$..."`,
  `printenv`, or `env |`.

## 4. Env-File Precheck Requirements

The env-file precheck must validate the file before sourcing it.

Allowed lines:

- blank lines;
- comments;
- static `KEY=VALUE` assignments;
- static `export KEY=VALUE` assignments.

Rejected before source:

- command substitution;
- backticks;
- `${...}` or `$[...]` expansion syntax;
- non-assignment commands;
- double-quoted values.

Values that need quoting must use single quotes.

## 5. Safety Boundaries

This task must not:

- connect to source or target databases;
- run row-copy;
- generate or accept operator evidence;
- mark any artifact ready for cutover;
- change `TENANCY_MODE`;
- add production cutover instructions.

## 6. Tests

Add focused tests proving:

- generated command files are accepted;
- out-of-order command files are rejected;
- command files that print DSN env vars are rejected;
- env files with command substitution are rejected without executing the
  substitution;
- env files with non-assignment commands are rejected without executing them;
- existing command-pack and full-closeout wrappers still pass.

## 7. Verification

Required commands:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_pack_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_full_closeout_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py

bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh
bash -n scripts/precheck_tenant_import_rehearsal_env_file.sh
git diff --check
```

## 8. Exit Criteria

- Focused safety tests pass.
- Wrapper regressions pass.
- Doc-index contracts pass after the new design/TODO/verification docs are
  indexed.
- `Ready for cutover: false` remains the only cutover state exposed by these
  tools.
