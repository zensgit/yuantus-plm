# Development Task - Phase 3 Tenant Import Env-File Precheck CLI Error Redaction

Date: 2026-05-05

## 1. Goal

Harden the P3.4 tenant import env-file precheck so CLI parse errors cannot echo
accidental DSN-like argument values or repo-external env-file paths.

This is local operator-safety hardening only. It does not source an env file,
connect to a database, execute row-copy, or close the external PostgreSQL
rehearsal evidence gate.

## 2. Background

The env-file precheck already validates file content before shell source and
keeps DSN values out of success and validation-failure output. The remaining
entrypoint gap was parse-time output before any env file was opened.

If an operator accidentally passes a DSN-like string as an unknown argument or
uses a missing env-file path containing sensitive path material, the shell
script should not echo that value back to stdout or stderr.

## 3. Required Output

- `scripts/precheck_tenant_import_rehearsal_env_file.sh`
- `src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_CLI_ERROR_REDACTION_TODO_20260505.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_ENV_FILE_PRECHECK_CLI_ERROR_REDACTION_20260505.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Replace raw parse-time echoing with fixed redacted markers:

```text
error: unknown argument
argument value hidden: true
```

and:

```text
error: --env-file does not exist
env-file path hidden: true
```

The precheck still exits with status `2` for parse/input errors and still
prints usage for unknown arguments, but it does not include the unsafe value.

## 5. Acceptance Criteria

- Unknown arguments still fail with exit code `2`.
- Unknown arguments containing `postgresql://user:secret@example.com/source` do
  not echo the DSN-like value.
- Missing env-file paths still fail with exit code `2`.
- Missing env-file paths containing `secret` do not echo the path.
- Valid repo-external env files still pass the precheck.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No env-file sourcing inside the precheck.
- No database connection.
- No row-copy rehearsal execution.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No change to successful validation output.

## 7. Verification

Run:

```bash
bash -n scripts/precheck_tenant_import_rehearsal_env_file.sh

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_env_file_precheck_shell.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
