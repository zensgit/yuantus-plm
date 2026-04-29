# Development Task — Phase 3 Tenant Import Evidence Handoff

Date: 2026-04-29

## 1. Goal

Add a DB-free evidence handoff gate for P3.4.2 tenant import rehearsal.

The gate validates that:

- the evidence archive manifest is ready;
- the redaction guard is ready;
- every artifact listed by the archive manifest was included in the redaction
  guard scan;
- `ready_for_cutover=false` remains pinned.

## 2. Context

P3.4 already has:

- row-copy rehearsal;
- evidence gate;
- archive manifest;
- external status;
- operator request;
- redaction guard.

The redaction guard accepts arbitrary artifact paths. Without a coverage gate,
an operator could accidentally scan only some artifacts and then hand off an
archive that contains unscanned files. This task closes that gap.

## 3. Scope

Add:

- `src/yuantus/scripts/tenant_import_rehearsal_evidence_handoff.py`;
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py`;
- runbook section `20.2 P3.4.2 Evidence Handoff Gate`;
- parent P3.4 TODO update;
- this task document;
- a TODO document;
- a DEV_AND_VERIFICATION document;
- delivery doc index entries.

## 4. Non-Goals

- No database connection.
- No row-copy rehearsal execution.
- No new evidence acceptance.
- No archive creation.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No production data import.

## 5. CLI Contract

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_handoff \
  --archive-json output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json \
  --redaction-guard-json output/tenant_<tenant-id>_redaction_guard.json \
  --output-json output/tenant_<tenant-id>_evidence_handoff.json \
  --output-md output/tenant_<tenant-id>_evidence_handoff.md \
  --strict
```

Strict mode exits 0 only when the archive and redaction guard are both green and
the redaction guard scanned every archived artifact path.

## 6. Validation Contract

The gate requires:

- archive schema version matches P3.4.2 archive manifest;
- archive has `ready_for_archive=true`;
- archive has `ready_for_cutover=false`;
- archive has no blockers;
- redaction guard schema version matches P3.4.2 redaction guard;
- redaction guard has `ready_for_artifact_handoff=true`;
- redaction guard has `ready_for_cutover=false`;
- redaction guard has no blockers;
- every archive artifact path appears in the redaction guard artifacts list.

## 7. Output Contract

The JSON report includes:

- `schema_version`;
- archive/redaction input paths and schema versions;
- tenant/schema/redacted target URL;
- archive and redaction artifact counts;
- archive artifact summary with hashes;
- `ready_for_evidence_handoff`;
- `ready_for_cutover=false`;
- blockers.

The Markdown report renders the same information for reviewer handoff.

## 8. Acceptance Criteria

- Green archive + green redaction guard with full coverage passes.
- Missing redaction coverage blocks.
- Blocked archive or blocked redaction guard blocks.
- CLI writes JSON and Markdown outputs.
- Source-scope test confirms no runtime tenancy mode, SQLAlchemy engine, or
  session usage.

## 9. Verification

Run:

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

## 10. Stop Rule

If the gate needs live databases or credentials to pass, stop. This task must
remain local-artifact-only.
