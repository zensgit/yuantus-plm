# Dev & Verification — Phase 3 Tenant Import Evidence Intake

Date: 2026-04-30

## 1. Summary

Added a DB-free P3.4.2 evidence intake checklist for tenant import rehearsal
artifacts.

The checklist validates the completed operator artifact set before reviewer
handoff. It rejects missing files, blocked JSON reports, synthetic drill output,
and plaintext PostgreSQL passwords.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_evidence_intake.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_EVIDENCE_INTAKE_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_EVIDENCE_INTAKE_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EVIDENCE_INTAKE_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The intake script reads the existing operator execution packet and inspects the
expected output paths from `outputs`.

It validates these eight artifacts:

- `rehearsal_json`;
- `rehearsal_md`;
- `operator_evidence_template_json`;
- `operator_evidence_md`;
- `evidence_json`;
- `evidence_md`;
- `archive_json`;
- `archive_md`.

JSON artifacts are checked for schema version, ready fields, empty blockers,
and `ready_for_cutover=false`. Markdown artifacts must be readable and
non-empty. Any artifact with synthetic drill markers is rejected.

The script then runs the existing redaction guard across the full artifact set.

## 4. Safety Boundaries

This PR does not:

- open database connections;
- run row-copy;
- accept operator evidence;
- build archive manifests;
- run the evidence handoff gate;
- authorize production cutover;
- enable runtime schema-per-tenant mode.

## 5. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_evidence_intake.py

git diff --check
```

## 6. Verification Results

- Evidence intake focused test: `8 passed in 0.23s`.
- Adjacent focused suite: `37 passed in 0.19s`.
- Full P3.4 focused suite + doc-index trio:
  `177 passed, 1 skipped, 1 warning in 1.19s`.
- Runbook/index contracts: `5 passed in 0.03s`.
- `py_compile`: passed.
- `git diff --check`: clean.

## 7. Remaining Work

The real external item is unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- production cutover remains blocked;
- runtime schema-per-tenant enablement remains blocked.
