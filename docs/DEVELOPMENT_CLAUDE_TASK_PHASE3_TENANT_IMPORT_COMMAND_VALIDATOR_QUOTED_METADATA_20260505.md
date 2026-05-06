# Development Task - Phase 3 Tenant Import Command Validator Quoted Metadata

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import generated command-file validator so quoted
evidence metadata arguments cannot carry shell variable expansion or escape
syntax.

This is local operator-safety hardening only. It does not execute generated
commands, connect to a database, or close the external PostgreSQL rehearsal
evidence gate.

## 2. Background

The command validator already restricts executable lines, option names, and
path-valued option arguments. The remaining quoted-field gap was evidence
metadata text under the evidence-template command.

Generated placeholders such as `"<owner>"` are safe, but a manually edited
command file could put values such as `"$SOURCE_DATABASE_URL"` into a metadata
field. Because shell double quotes still expand variables, that edit could leak
an environment variable into generated evidence before review.

## 3. Required Output

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_QUOTED_METADATA_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_QUOTED_METADATA_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Add one shared validator regex for quoted evidence metadata values:

```text
"[^"$`\\]+"
```

Apply it only to evidence-template metadata fields:

- `--backup-restore-owner`
- `--rehearsal-window`
- `--rehearsal-executed-by`
- `--evidence-reviewer`
- `--evidence-date`

The rule keeps generated placeholder text and ordinary human text valid while
rejecting shell variable expansion and backslash escape syntax.

## 5. Acceptance Criteria

- Generated command files still pass validation.
- Quoted metadata values containing `$SOURCE_DATABASE_URL` fail.
- Quoted metadata values containing backslash escape syntax fail.
- Failure output reports only the line number and command step, not the edited
  value.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No generated command execution.
- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No filesystem validation for artifact paths.

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
