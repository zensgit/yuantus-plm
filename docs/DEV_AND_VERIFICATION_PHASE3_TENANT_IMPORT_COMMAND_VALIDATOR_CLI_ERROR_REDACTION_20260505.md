# Dev & Verification - Phase 3 Tenant Import Command Validator CLI Error Redaction

Date: 2026-05-05

## 1. Summary

Redacted parse-time CLI errors from the P3.4 tenant import generated
command-file validator.

The validator no longer echoes raw unknown argument values or missing
command-file paths. This closes an entrypoint error path that existed before a
command file was opened.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_CLI_ERROR_REDACTION_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_CLI_ERROR_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_CLI_ERROR_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

Unknown arguments now emit:

```text
error: unknown argument
argument value hidden: true
```

Missing command-file paths now emit:

```text
error: command file does not exist
command file path hidden: true
```

The script keeps exit code `2` for these input errors. Unknown arguments still
print usage so operators can recover without exposing the rejected value.

## 4. Regression Coverage

The command-validator tests now cover:

- unknown argument containing `postgresql://user:secret@example.com/source`;
- missing command-file path containing `secret`;
- hidden-value markers present;
- DSN-like substrings absent from combined stdout/stderr;
- generated command file still accepted.

The stop-gate contracts pin the runbook/readiness language and keep the
operator-run PostgreSQL evidence item unchecked.

## 5. Verification Commands

```bash
bash -n scripts/validate_tenant_import_rehearsal_operator_commands.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 6. Verification Results

- Shell syntax: passed.
- Direct command-validator shell suite: 27 passed.
- Focused regression with stop-gate and doc-index contracts: 41 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
