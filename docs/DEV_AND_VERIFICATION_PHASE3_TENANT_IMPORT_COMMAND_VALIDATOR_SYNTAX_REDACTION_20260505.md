# Dev & Verification - Phase 3 Tenant Import Command Validator Syntax Redaction

Date: 2026-05-05

## 1. Summary

Redacted raw shell syntax diagnostics from the P3.4 tenant import generated
command-file validator.

The validator still runs `bash -n`, but syntax failures now report a fixed
redacted marker instead of returning raw Bash diagnostics that may include the
edited command line.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SYNTAX_REDACTION_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SYNTAX_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SYNTAX_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The validator keeps this behavior:

```bash
bash -n "$command_file"
```

The public blocker list changed from raw diagnostics to fixed messages:

```text
shell syntax failed
shell syntax details hidden: true
```

This preserves operator feedback while preventing syntax-error output from
leaking DSN-like strings, command fragments, or secret-bearing edits.

## 4. Regression Coverage

The command-validator tests now cover:

- generated command file still accepted;
- normal shell syntax error still rejected;
- syntax error containing `postgresql://user:secret@example.com/source`
  rejected;
- raw syntax-error command line not echoed;
- `postgresql://user` and `secret` not echoed;
- redacted syntax marker present.

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
- Direct command-validator shell suite: 25 passed.
- Focused regression with stop-gate and doc-index contracts: 39 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
