# Development Task - Phase 3 Tenant Import Shell Wrapper CLI Error Redaction

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import shell wrapper entrypoints so unknown CLI argument
errors cannot echo accidental DSN-like values.

This is local operator-safety hardening only. It does not connect to a database,
execute row-copy, accept evidence, build closeout archives, or close the
external PostgreSQL rehearsal evidence gate.

## 2. Background

The command-file validator and env-file precheck already redact their parse-time
CLI errors. The surrounding operator shell wrappers still had the older pattern:

```bash
echo "error: unknown argument: $1" >&2
```

That meant an accidental argument such as
`--bad=postgresql://user:secret@example.com/source` could be echoed before any
tool-specific validation happened.

## 3. Required Output

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
- `docs/PHASE3_TENANT_IMPORT_SHELL_WRAPPER_CLI_ERROR_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SHELL_WRAPPER_CLI_ERROR_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Replace raw parse-time echoing with fixed redacted markers:

```text
error: unknown argument
argument value hidden: true
```

The wrappers still exit with status `2` and still print usage so operators can
recover without exposing the rejected value.

## 5. Acceptance Criteria

- Each affected wrapper still rejects unknown arguments with exit code `2`.
- Unknown arguments containing `postgresql://user:secret@example.com/source` do
  not echo the DSN-like value.
- Usage output remains available.
- Existing wrapper success paths and required-argument failures are unchanged.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No database connection.
- No row-copy rehearsal execution.
- No evidence acceptance or archive generation.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No rewrite of Python CLI error handling.

## 7. Verification

Run:

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
  src/yuantus/tests/test_tenant_import_rehearsal_shell_wrapper_cli_error_redaction.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
