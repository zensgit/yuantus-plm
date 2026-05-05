# Dev & Verification - Phase 3 Tenant Import Command Validator Line Allowlist

Date: 2026-05-05

## 1. Summary

Added executable-line allowlist validation to the P3.4 tenant import generated
operator command-file validator.

The validator now rejects unsupported executable lines before an operator uses
the generated file. This closes the gap where an edited command file could add
an extra command that did not match an existing forbidden pattern.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_LINE_ALLOWLIST_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_LINE_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_LINE_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

`validate_allowed_command_lines()` scans each non-comment, non-blank command
file line. The accepted shapes are the generated tenant import script commands,
`set -a`, `set +a`, the generated env-file source line, and option continuation
lines beginning with `--`.

Unsupported lines fail with a line-number-only error:

```text
unsupported command line <n>; only generated tenant import commands are allowed
```

Shell-control syntax fails with:

```text
forbidden shell control syntax on line <n>
```

Both error shapes intentionally avoid echoing the rejected line.

## 4. Regression Coverage

The command-validator tests now cover:

- generated command file still accepted;
- extra `rm -rf output` rejected without echoing the line;
- extra `python -c` rejected without echoing embedded DSN secrets;
- extra `export PATH=/tmp/blocked` rejected without echoing the line;
- shell-control syntax rejected without echoing the line.

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
- Direct command-validator shell suite: 15 passed.
- Focused regression with stop-gate and doc-index contracts: 29 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
