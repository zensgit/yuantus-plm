# Development Task - Phase 3 Tenant Import Python CLI Error Redaction

Date: 2026-05-06

## 1. Goal

Harden the P3.4 tenant import Python module entrypoints so parse-time CLI
errors cannot echo accidental DSN-like values.

This is local operator-safety hardening only. It does not connect to a database,
execute row-copy, accept operator evidence, build closeout archives, or close
the external PostgreSQL rehearsal evidence gate.

## 2. Background

The command-file validator, env-file precheck, and shell wrappers already hide
raw unknown argument values. The Python module entrypoints still used default
`argparse.ArgumentParser` behavior:

```text
error: unrecognized arguments: --bad=postgresql://user:secret@example.com/source
```

That output can expose DSN-like values before any domain-specific validation
runs.

## 3. Required Output

- `src/yuantus/scripts/tenant_import_cli_safety.py`
- all `src/yuantus/scripts/tenant_import_rehearsal*.py` CLI parser call sites
- `src/yuantus/tests/test_tenant_import_rehearsal_python_cli_error_redaction.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_PYTHON_CLI_ERROR_REDACTION_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_PYTHON_CLI_ERROR_REDACTION_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Design

Add a shared `RedactingArgumentParser` for tenant import scripts. Its
`error(...)` path keeps usage output and exit code `2`, but replaces the raw
`argparse` error with fixed markers:

```text
error: CLI parse failed
argument value hidden: true
```

Only parse-time CLI errors are changed. Runtime validation errors remain scoped
to the existing script contracts because those messages are already part of the
operator workflow.

## 5. Acceptance Criteria

- Every `tenant_import_rehearsal*.py` module CLI uses the shared redacting
  parser.
- Unknown arguments containing `postgresql://user:secret@example.com/source` do
  not echo the DSN-like value.
- Exit code `2` is preserved for parse-time failures.
- Usage output remains available.
- P3.4 operator-run PostgreSQL evidence remains unchecked.

## 6. Non-Goals

- No database connection.
- No row-copy rehearsal execution.
- No evidence acceptance or archive generation.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No rewrite of script runtime exception messages.

## 7. Verification

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_python_cli_error_redaction.py

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  src/yuantus/scripts/tenant_import_cli_safety.py \
  src/yuantus/scripts/tenant_import_rehearsal*.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_python_cli_error_redaction.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
