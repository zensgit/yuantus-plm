# Development Task - Phase 3 Tenant Import Command Validator Syntax Redaction

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import generated command-file validator so shell syntax
diagnostics cannot echo edited command-file content.

This is local operator-safety hardening only. It does not execute generated
commands, connect to a database, or close the external PostgreSQL rehearsal
evidence gate.

## 2. Background

The validator already avoids echoing rejected unsupported lines, option values,
path rewrites, and quoted metadata edits. One diagnostic path still depended on
`bash -n` output.

When a command file has a syntax error, Bash can include the raw offending line
in its diagnostic output. If that line contains a DSN-like value or secret
fragment, returning the raw diagnostic would bypass the validator's no-echo
failure boundary.

## 3. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SYNTAX_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SYNTAX_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Keep `bash -n` as the shell syntax gate, but do not append raw `bash -n`
diagnostic output to the public blocker list.

On syntax failure, report:

```text
shell syntax failed
shell syntax details hidden: true
```

The operator still gets a precise failure class while the edited command-file
content remains hidden from stdout.

## 5. Acceptance Criteria

- Generated command files still pass validation.
- Plain shell syntax errors still fail validation.
- Syntax errors containing DSN-like text fail validation.
- Syntax failure output does not echo the raw offending line.
- Syntax failure output does not echo `postgresql://`, `secret`, or the edited
  command.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No generated command execution.
- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No replacement of Bash syntax validation.

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
