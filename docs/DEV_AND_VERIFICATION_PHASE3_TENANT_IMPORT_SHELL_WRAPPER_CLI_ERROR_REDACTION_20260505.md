# Dev & Verification - Phase 3 Tenant Import Shell Wrapper CLI Error Redaction

Date: 2026-05-05

## 1. Summary

Redacted unknown-argument CLI errors across the P3.4 tenant import shell wrapper
entrypoints.

The wrappers no longer echo raw unknown argument values. This closes the
remaining shell-entrypoint parse-time path where accidental DSN-like values
could be printed before validation.

## 2. Files Changed

- `scripts/generate_tenant_import_rehearsal_env_template.sh`
- `scripts/precheck_tenant_import_rehearsal_operator.sh`
- `scripts/prepare_tenant_import_rehearsal_operator_commands.sh`
- `scripts/print_tenant_import_rehearsal_commands.sh`
- `scripts/run_tenant_import_operator_launchpack.sh`
- `scripts/run_tenant_import_rehearsal_operator_sequence.sh`
- `scripts/run_tenant_import_rehearsal_full_closeout.sh`
- `scripts/precheck_tenant_import_rehearsal_evidence.sh`
- `scripts/run_tenant_import_evidence_closeout.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_shell_wrapper_cli_error_redaction.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_SHELL_WRAPPER_CLI_ERROR_REDACTION_20260505.md`
- `docs/PHASE3_TENANT_IMPORT_SHELL_WRAPPER_CLI_ERROR_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SHELL_WRAPPER_CLI_ERROR_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

Unknown arguments now emit:

```text
error: unknown argument
argument value hidden: true
```

The wrappers keep exit code `2` for parse errors and still print usage. The raw
argument value is not included in stdout or stderr.

## 4. Regression Coverage

The new parameterized shell test covers all affected wrappers with a DSN-like
unknown argument:

- `generate_tenant_import_rehearsal_env_template.sh`
- `precheck_tenant_import_rehearsal_operator.sh`
- `prepare_tenant_import_rehearsal_operator_commands.sh`
- `print_tenant_import_rehearsal_commands.sh`
- `run_tenant_import_operator_launchpack.sh`
- `run_tenant_import_rehearsal_operator_sequence.sh`
- `run_tenant_import_rehearsal_full_closeout.sh`
- `precheck_tenant_import_rehearsal_evidence.sh`
- `run_tenant_import_evidence_closeout.sh`

The stop-gate contracts pin the runbook/readiness language and keep the
operator-run PostgreSQL evidence item unchecked.

## 5. Verification Commands

```bash
bash -n \
  scripts/generate_tenant_import_rehearsal_env_template.sh \
  scripts/precheck_tenant_import_rehearsal_operator.sh \
  scripts/prepare_tenant_import_rehearsal_operator_commands.sh \
  scripts/print_tenant_import_rehearsal_commands.sh \
  scripts/run_tenant_import_operator_launchpack.sh \
  scripts/run_tenant_import_rehearsal_operator_sequence.sh \
  scripts/run_tenant_import_rehearsal_full_closeout.sh \
  scripts/precheck_tenant_import_rehearsal_evidence.sh \
  scripts/run_tenant_import_evidence_closeout.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_shell_wrapper_cli_error_redaction.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_shell_wrapper_cli_error_redaction.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## 6. Verification Results

- Shell syntax: passed.
- Direct shell-wrapper redaction suite: 9 passed.
- Focused shell-wrapper plus stop-gate regression: 19 passed.
- `git diff --check`: clean.

Local doc-index completeness is blocked by unrelated untracked CAD material sync
plugin files in this worktree:

```text
docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md
docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md
plugins/yuantus-cad-material-sync/
src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
```

Those files are intentionally not included in this P3.4 PR. The GitHub PR runs
doc-index contracts from the clean branch state.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
