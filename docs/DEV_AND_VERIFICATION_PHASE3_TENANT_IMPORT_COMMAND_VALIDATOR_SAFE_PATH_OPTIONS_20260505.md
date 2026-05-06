# Dev & Verification - Phase 3 Tenant Import Command Validator Safe Path Options

Date: 2026-05-05

## 1. Summary

Restricted generated command-file path-valued option arguments to a safe
artifact path token set.

The validator now rejects path edits containing shell redirection, variable
expansion, or quoted path rewrites while preserving the existing no-echo failure
boundary.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SAFE_PATH_OPTIONS_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SAFE_PATH_OPTIONS_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_SAFE_PATH_OPTIONS_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

`validate_tenant_import_rehearsal_operator_commands.sh` now defines one shared
safe path regex:

```text
[-A-Za-z0-9_./:]+
```

Generated artifact path options in launchpack, row-copy, evidence-template,
evidence-gate, and evidence-closeout steps must match that token set. Human
sign-off fields remain quoted strings and are not treated as artifact paths.

## 4. Regression Coverage

The command-validator tests now cover:

- generated command file still accepted;
- output redirection in row-copy `--output-json` rejected;
- input redirection in closeout `--artifact-prefix` rejected;
- `$HOME` expansion in launchpack `--operator-packet-json` rejected;
- quoted path rewrite in evidence-gate `--output-md` rejected;
- rejected path values are not echoed.

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
- Direct command-validator shell suite: 22 passed.
- Focused regression with stop-gate and doc-index contracts: 36 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
