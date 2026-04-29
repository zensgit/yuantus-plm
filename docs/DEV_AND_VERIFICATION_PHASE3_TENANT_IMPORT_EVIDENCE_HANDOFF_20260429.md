# Dev & Verification — Phase 3 Tenant Import Evidence Handoff

Date: 2026-04-29

## 1. Summary

Added a DB-free P3.4.2 evidence handoff gate for tenant import rehearsal
artifacts.

The new gate ties the archive manifest to the redaction guard and blocks
handoff unless every archived artifact was included in the redaction scan.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_evidence_handoff.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_EVIDENCE_HANDOFF_20260429.md`
- `docs/PHASE3_TENANT_IMPORT_EVIDENCE_HANDOFF_TODO_20260429.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EVIDENCE_HANDOFF_20260429.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The evidence handoff gate reads two local JSON artifacts:

- archive manifest JSON;
- redaction guard JSON.

It validates that both reports are green and then compares path coverage:

```text
archive.artifacts[*].path ⊆ redaction_guard.artifacts[*].path
```

Paths are compared by resolved filesystem path when both files exist, otherwise
by literal path text. This keeps the gate deterministic for generated artifacts
and still handles relative-path reports.

## 4. Safety Boundaries

This PR does not:

- open database connections;
- run row-copy;
- accept new operator evidence;
- build archive manifests;
- authorize production cutover;
- import production data;
- enable `TENANCY_MODE=schema-per-tenant`.

The source-level contract test also asserts that the new script does not import
runtime tenancy mode, SQLAlchemy engines, or sessions.

## 5. Failure Modes Covered

- Archive manifest is blocked.
- Redaction guard is blocked.
- Archive or redaction guard has wrong schema version.
- Either report flips `ready_for_cutover=true`.
- Redaction guard omits an archive artifact path.
- CLI strict mode exits 1 when coverage is incomplete.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
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
  src/yuantus/scripts/tenant_import_rehearsal_evidence_handoff.py

git diff --check
```

## 7. Verification Results

- Evidence handoff + adjacent archive/redaction/status + doc-index focused
  suite: `34 passed in 0.36s`.
- Full P3.4 focused suite + doc-index trio:
  `157 passed, 1 skipped, 1 warning in 1.33s`.
- Runbook/index contracts: `5 passed in 0.03s`.
- `py_compile`: passed.
- `git diff --check`: clean.

## 8. Remaining External Work

The next real transition still requires external operator execution:

- run row-copy rehearsal against non-production PostgreSQL;
- generate real operator evidence;
- run evidence gate against real operator evidence;
- build archive manifest;
- run redaction guard against real artifacts;
- run this evidence handoff gate against the real archive/redaction outputs;
- keep production cutover blocked until separately authorized.
