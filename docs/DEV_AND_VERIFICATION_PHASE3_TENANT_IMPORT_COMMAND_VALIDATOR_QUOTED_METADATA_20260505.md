# Dev & Verification - Phase 3 Tenant Import Command Validator Quoted Metadata

Date: 2026-05-05

## 1. Summary

Restricted generated command-file quoted evidence metadata arguments to literal
metadata text that cannot trigger shell variable expansion or backslash escape
handling.

The validator now rejects edited metadata values such as
`"$SOURCE_DATABASE_URL"` or `"ops\reviewer"` while preserving the existing
no-echo failure boundary.

## 2. Files Changed

- `scripts/validate_tenant_import_rehearsal_operator_commands.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_command_validator_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_QUOTED_METADATA_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_QUOTED_METADATA_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_COMMAND_VALIDATOR_QUOTED_METADATA_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

`validate_tenant_import_rehearsal_operator_commands.sh` now defines one shared
quoted metadata regex:

```text
"[^"$`\\]+"
```

Evidence-template metadata options must match that token. The rule is narrower
than the previous `"[^\"]+"` pattern because shell double quotes still expand
variables. Rejecting `$` and backslash prevents the generated command file from
injecting environment expansion into evidence metadata.

## 4. Regression Coverage

The command-validator tests now cover:

- generated command file still accepted;
- `$SOURCE_DATABASE_URL` expansion in `--backup-restore-owner` rejected;
- backslash escape syntax in `--evidence-reviewer` rejected;
- rejected metadata values are not echoed.

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
- Direct command-validator shell suite: 24 passed.
- Focused regression with stop-gate and doc-index contracts: 38 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
