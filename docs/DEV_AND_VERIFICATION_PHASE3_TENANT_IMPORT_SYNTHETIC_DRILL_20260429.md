# Dev & Verification — Phase 3 Tenant Import Synthetic Drill

Date: 2026-04-29

## 1. Summary

Added a DB-free P3.4.2 synthetic operator drill for the tenant import rehearsal
toolchain.

The drill generates visibly synthetic local artifacts and runs the existing
redaction guard against them. It is an operator command-path rehearsal only; it
does not satisfy the real operator-run PostgreSQL evidence stop gate.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_synthetic_drill.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_20260429.md`
- `docs/PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_TODO_20260429.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_20260429.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The new script has one job: prove the local artifact path and redaction tooling
work without requiring source or target database access.

It writes three synthetic artifacts:

- synthetic operator evidence Markdown;
- synthetic external status JSON;
- synthetic operator notes Markdown.

It then calls `tenant_import_rehearsal_redaction_guard` against those synthetic
files and writes a drill report.

## 4. Deliberate Non-Evidence Boundary

The report pins all real-evidence and cutover gates closed:

- `synthetic_drill=true`;
- `real_rehearsal_evidence=false`;
- `db_connection_attempted=false`;
- `ready_for_operator_evidence=false`;
- `ready_for_evidence_handoff=false`;
- `ready_for_cutover=false`.

The script does not import or call the real evidence archive or evidence
handoff gate.

## 5. Secret Handling

The test-only plaintext injection path verifies that the redaction guard blocks
unredacted PostgreSQL passwords and that the generated drill report does not
leak the plaintext secret.

The failure report includes only the redacted URL.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
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
  src/yuantus/scripts/tenant_import_rehearsal_synthetic_drill.py

git diff --check
```

## 7. Verification Results

- Synthetic drill focused test: `7 passed in 0.07s`.
- Adjacent P3.4 artifact-chain suite: `48 passed in 0.44s`.
- Full P3.4 focused suite + doc-index trio:
  `164 passed, 1 skipped, 1 warning in 1.18s`.
- Runbook/index contracts: `5 passed in 0.04s`.
- `py_compile`: passed.
- `git diff --check`: clean.

## 8. Remaining External Work

The actual stop-gate item remains unchanged:

- operator-run PostgreSQL rehearsal evidence is still missing;
- production cutover is still blocked;
- runtime schema-per-tenant enablement is still blocked.
