# Development Task — Phase 3 Tenant Import Redaction Guard

Date: 2026-04-29

## 1. Goal

Add a DB-free redaction guard for P3.4.2 tenant import rehearsal artifacts.

The guard scans JSON/Markdown handoff files for plaintext PostgreSQL passwords
before those artifacts are handed to reviewers or archived.

## 2. Context

The P3.4.2 toolchain already redacts URLs in generated reports. Real operator
evidence, however, can include hand-written Markdown. A separate artifact-level
guard gives operators a final local check before evidence handoff.

## 3. Scope

Add:

- `src/yuantus/scripts/tenant_import_rehearsal_redaction_guard.py`;
- `src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py`;
- runbook section `20.1 P3.4.2 Artifact Redaction Guard`;
- parent P3.4 TODO update;
- this task document;
- a TODO document;
- a DEV_AND_VERIFICATION document;
- delivery doc index entries.

## 4. Non-Goals

- No database connection.
- No row-copy rehearsal execution.
- No operator evidence acceptance.
- No archive creation.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No printing plaintext secret values in guard output.

## 5. CLI Contract

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_redaction_guard \
  --artifact output/tenant_<tenant-id>_import_rehearsal.json \
  --artifact output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --output-json output/tenant_<tenant-id>_redaction_guard.json \
  --output-md output/tenant_<tenant-id>_redaction_guard.md \
  --strict
```

Strict mode exits 0 only when every provided artifact exists, is readable, and
contains no unredacted PostgreSQL password.

## 6. Detection Rule

The guard scans for PostgreSQL URLs and parses them with SQLAlchemy URL parsing.
It blocks when a URL contains a password that is not an accepted redaction token
such as `***`, `<redacted>`, or `redacted`.

Blocker output must include only:

- artifact path;
- line number;
- redacted URL.

It must not include the plaintext password.

## 7. Output Contract

The JSON report includes:

- `schema_version`;
- artifact count;
- artifact statuses;
- URL count per artifact;
- plaintext password count per artifact;
- `ready_for_artifact_handoff`;
- `ready_for_cutover=false`;
- blockers.

The Markdown report renders the same information for operator handoff.

## 8. Acceptance Criteria

- Redacted PostgreSQL URLs pass.
- Plaintext PostgreSQL passwords fail and are not echoed.
- Missing artifacts fail.
- Empty artifact list fails.
- CLI writes JSON and Markdown outputs.
- Source-scope test confirms no runtime tenancy mode, SQLAlchemy engine, or
  session usage.

## 9. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_redaction_guard.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
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
  src/yuantus/scripts/tenant_import_rehearsal_redaction_guard.py

git diff --check
```

## 10. Stop Rule

If the guard needs real credentials or a live database to pass, stop. This task
must remain local-file-only.
