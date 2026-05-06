# Development Task - Phase 3 Tenant Import Command Validator CLI Error Redaction

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import generated command-file validator so CLI parse
errors cannot echo accidental DSN-like argument values or command-file paths.

This is local operator-safety hardening only. It does not execute generated
commands, connect to a database, or close the external PostgreSQL rehearsal
evidence gate.

## 2. Background

The validator already redacts generated command-file content, unsupported line
values, option values, quoted metadata edits, and raw shell syntax diagnostics.
The remaining entrypoint gap was parse-time output before a command file is
opened.

If an operator accidentally passes a DSN-like string as an unknown argument or
as a non-existent command-file path, the shell script should not echo that value
back to stdout or stderr.

## 3. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_CLI_ERROR_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_CLI_ERROR_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Replace raw parse-time echoing with fixed redacted markers:

```text
error: unknown argument
argument value hidden: true
```

and:

```text
error: command file does not exist
command file path hidden: true
```

The validator still exits with status `2` for parse/input errors and still
prints usage for unknown arguments, but it does not include the unsafe value.

## 5. Acceptance Criteria

- Unknown arguments still fail with exit code `2`.
- Unknown arguments containing `postgresql://user:secret@example.com/source` do
  not echo the DSN-like value.
- Missing command-file paths still fail with exit code `2`.
- Missing command-file paths containing `secret` do not echo the path.
- Generated command files still pass validation.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No generated command execution.
- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No change to successful validation output.

## 7. Verification

Run:

```bash
bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
