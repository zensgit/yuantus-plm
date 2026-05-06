# Development Task - Phase 3 Tenant Import Command Validator Safe Path Options

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import generated command-file validator so path-valued
option arguments cannot carry shell redirection, variable expansion, or quoted
path rewrites.

This is local operator-safety hardening only. It does not execute generated
commands, connect to a database, or close the external PostgreSQL rehearsal
evidence gate.

## 2. Background

The validator already restricts executable lines and command-step-aware option
names. The remaining gap was the option value shape for artifact paths.

Generated paths are simple artifact tokens. A manually edited command file could
still put characters such as `>`, `<`, `$`, or quotes inside path-valued option
arguments. Those edits should not pass a static generated-command validator.

## 3. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SAFE_PATH_OPTIONS_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SAFE_PATH_OPTIONS_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Add one shared validator regex for path-like generated option values:

```text
[-A-Za-z0-9_./:]+
```

Apply it to generated artifact path options in these command steps:

- operator launchpack;
- row-copy rehearsal;
- evidence template;
- evidence gate;
- evidence closeout.

Do not apply this rule to quoted human sign-off fields such as owner, window,
operator, reviewer, or evidence date. Those fields are not artifact paths.

## 5. Acceptance Criteria

- Generated command files still pass validation.
- Path values containing output redirection (`>`) fail.
- Path values containing input redirection (`<`) fail.
- Path values containing shell variable expansion (`$HOME`) fail.
- Quoted path rewrites fail.
- Failure output reports only the line number and command step, not the edited
  value.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No generated command execution.
- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No attempt to validate filesystem existence of artifact paths.

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
