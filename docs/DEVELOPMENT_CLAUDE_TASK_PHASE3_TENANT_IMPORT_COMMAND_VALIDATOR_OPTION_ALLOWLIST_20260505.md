# Development Task - Phase 3 Tenant Import Command Validator Option Allowlist

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import generated command-file validator so continuation
option lines are allowed only in the generated command step they belong to.

This prevents an edited command file from inserting unknown options, moving
known options into the wrong command, or appending orphan option lines while
still passing static validation.

## 2. Background

The command validator already rejects unsupported executable lines. The
remaining local safety gap was option-line scope: any line beginning with `--`
was accepted as a generated continuation line.

That meant edits such as the following could pass the line-level allowlist:

- adding `--confirm-cutover` inside the row-copy command;
- moving `--output-json output/hijack.json` into the env precheck command;
- appending a standalone `--strict` line after the generated sequence.

## 3. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_OPTION_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_OPTION_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

The validator now tracks the current generated command step while scanning the
command file. Command-start lines set the current step. Continuation option
lines are checked against the allowed option set for that specific step.

Examples:

- `--env-file` is allowed under the env precheck step.
- `--output-json` is allowed under row-copy/evidence steps, but not under env
  precheck.
- `--strict` is allowed under the evidence gate step only.
- `--confirm-cutover` is not allowed in any generated step.

Errors report only the line number and command step name. The validator does not
echo the rejected line, preserving the existing secret-redaction boundary.

## 5. Acceptance Criteria

- Generated command files still pass validation.
- Unknown option lines inside a command block fail.
- Known option lines in the wrong command block fail.
- Orphan option lines outside a generated command block fail.
- Failure output does not echo rejected option-line values.
- The fix remains DB-free and does not execute generated commands.
- P3.4 real operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No generated command execution.
- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

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
