# Dev & Verification - Phase 3 Tenant Import Python CLI Error Redaction

Date: 2026-05-06

## 1. Summary

Redacted parse-time CLI errors across the P3.4 tenant import Python module
entrypoints.

The modules no longer echo raw unknown argument values from default `argparse`
diagnostics. This closes the Python-entrypoint parse-time path where accidental
DSN-like values could be printed before validation.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_cli_safety.py`
- `src/yuantus/scripts/tenant_import_rehearsal.py`
- `src/yuantus/scripts/tenant_import_rehearsal_evidence.py`
- `src/yuantus/scripts/tenant_import_rehearsal_evidence_archive.py`
- `src/yuantus/scripts/tenant_import_rehearsal_evidence_handoff.py`
- `src/yuantus/scripts/tenant_import_rehearsal_evidence_intake.py`
- `src/yuantus/scripts/tenant_import_rehearsal_evidence_template.py`
- `src/yuantus/scripts/tenant_import_rehearsal_external_status.py`
- `src/yuantus/scripts/tenant_import_rehearsal_handoff.py`
- `src/yuantus/scripts/tenant_import_rehearsal_implementation_packet.py`
- `src/yuantus/scripts/tenant_import_rehearsal_next_action.py`
- `src/yuantus/scripts/tenant_import_rehearsal_operator_bundle.py`
- `src/yuantus/scripts/tenant_import_rehearsal_operator_flow.py`
- `src/yuantus/scripts/tenant_import_rehearsal_operator_launchpack.py`
- `src/yuantus/scripts/tenant_import_rehearsal_operator_packet.py`
- `src/yuantus/scripts/tenant_import_rehearsal_operator_request.py`
- `src/yuantus/scripts/tenant_import_rehearsal_plan.py`
- `src/yuantus/scripts/tenant_import_rehearsal_readiness.py`
- `src/yuantus/scripts/tenant_import_rehearsal_redaction_guard.py`
- `src/yuantus/scripts/tenant_import_rehearsal_reviewer_packet.py`
- `src/yuantus/scripts/tenant_import_rehearsal_source_preflight.py`
- `src/yuantus/scripts/tenant_import_rehearsal_synthetic_drill.py`
- `src/yuantus/scripts/tenant_import_rehearsal_target_preflight.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_python_cli_error_redaction.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_PYTHON_CLI_ERROR_REDACTION_20260506.md`
- `docs/PHASE3_TENANT_IMPORT_PYTHON_CLI_ERROR_REDACTION_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_PYTHON_CLI_ERROR_REDACTION_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The new `RedactingArgumentParser` emits:

```text
error: CLI parse failed
argument value hidden: true
```

It preserves usage output and exit code `2`. The raw rejected argument value is
not included in stdout or stderr.

The scope is parse-time CLI diagnostics only. Runtime `ValueError` and domain
validation messages stay on their existing paths.

## 4. Regression Coverage

The new parameterized Python CLI test covers all 22 affected modules with a
DSN-like unknown argument:

- `tenant_import_rehearsal`
- `tenant_import_rehearsal_evidence`
- `tenant_import_rehearsal_evidence_archive`
- `tenant_import_rehearsal_evidence_handoff`
- `tenant_import_rehearsal_evidence_intake`
- `tenant_import_rehearsal_evidence_template`
- `tenant_import_rehearsal_external_status`
- `tenant_import_rehearsal_handoff`
- `tenant_import_rehearsal_implementation_packet`
- `tenant_import_rehearsal_next_action`
- `tenant_import_rehearsal_operator_bundle`
- `tenant_import_rehearsal_operator_flow`
- `tenant_import_rehearsal_operator_launchpack`
- `tenant_import_rehearsal_operator_packet`
- `tenant_import_rehearsal_operator_request`
- `tenant_import_rehearsal_plan`
- `tenant_import_rehearsal_readiness`
- `tenant_import_rehearsal_redaction_guard`
- `tenant_import_rehearsal_reviewer_packet`
- `tenant_import_rehearsal_source_preflight`
- `tenant_import_rehearsal_synthetic_drill`
- `tenant_import_rehearsal_target_preflight`

The stop-gate contracts pin the runbook/readiness language and keep the
operator-run PostgreSQL evidence item unchecked.

## 5. Verification Commands

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

## 6. Verification Results

- Direct Python CLI redaction suite: 22 passed.
- `py_compile`: passed.
- Focused Python CLI plus stop-gate/doc-index regression: 36 passed.
- `git diff --check`: clean.

## 7. Remaining Work

External operator execution remains the blocker:

- provide real non-production source/target DSNs in a repo-external env file;
- run the PostgreSQL rehearsal during the approved window;
- submit real operator evidence for review.

This PR does not mark P3.4 complete.
