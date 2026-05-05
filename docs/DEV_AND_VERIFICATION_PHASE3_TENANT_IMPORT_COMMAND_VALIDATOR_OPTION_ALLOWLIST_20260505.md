# Dev & Verification - Phase 3 Tenant Import Command Validator Option Allowlist

Date: 2026-05-05

## 1. Summary

Added command-step-aware option-line validation to the P3.4 tenant import
generated operator command-file validator.

The validator now rejects option lines that are unknown, placed under the wrong
generated command, or orphaned outside a generated command block.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_OPTION_ALLOWLIST_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_OPTION_ALLOWLIST_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_OPTION_ALLOWLIST_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

`validate_allowed_command_lines()` now keeps `current_command` while scanning
the generated command file.

Command-start lines assign one of these generated steps:

- `env_template`
- `env_precheck`
- `launchpack`
- `row_copy`
- `evidence_template`
- `evidence_gate`
- `evidence_closeout`

Each `--...` continuation line is normalized by removing a trailing continuation
backslash, then matched against the option allowlist for the current command.
When a continuation line does not end in a backslash, the current command step
is closed.

## 4. Regression Coverage

The command-validator tests now cover:

- generated command file still accepted;
- `--confirm-cutover` rejected inside the row-copy block;
- `--output-json output/hijack.json` rejected inside the env precheck block;
- orphan `--strict` rejected outside generated command blocks;
- rejected option values are not echoed.

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
- Direct command-validator shell suite: 18 passed.
- Focused regression with stop-gate and doc-index contracts: 32 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
