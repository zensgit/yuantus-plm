# Development Task - Phase 3 Tenant Import Rehearsal Evidence Archive

Date: 2026-04-29

## 1. Goal

Add a DB-free archive manifest generator for completed P3.4.2 tenant import
rehearsal evidence.

The manifest records each artifact in the evidence chain with path, byte size,
schema version, ready field, and SHA-256 digest.

## 2. Rationale

After the row-copy, operator evidence template, and evidence gate are complete,
the remaining work is operator-run non-production rehearsal evidence. When that
happens, reviewers need one immutable handoff artifact that proves the evidence
files are present, hashable, and internally consistent.

## 3. Scope

- Add `src/yuantus/scripts/tenant_import_rehearsal_evidence_archive.py`.
- Add `src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py`.
- Update `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- Update P3.4 TODO docs and `docs/DELIVERY_DOC_INDEX.md`.
- Add DEV/verification and TODO docs for the archive manifest.

## 4. Non-Goals

- No database connections.
- No row-copy execution.
- No evidence modification.
- No schema creation, migration, downgrade, cleanup, or rollback.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 5. CLI Shape

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_archive \
  --evidence-json output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --operator-evidence-template-json output/tenant_<tenant-id>_operator_rehearsal_evidence_template.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_evidence_archive.md \
  --strict
```

If the operator evidence Markdown was hand-written, omit
`--operator-evidence-template-json`.

## 6. Required Validations

- Evidence report schema is `p3.4.2-tenant-import-rehearsal-evidence-v1`.
- Evidence report has `ready_for_rehearsal_evidence=true`.
- Evidence report has `operator_rehearsal_evidence_accepted=true`.
- Evidence report has `ready_for_cutover=false`.
- Evidence report has no blockers.
- Implementation packet, rehearsal JSON, operator evidence MD, and upstream
  dry-run/readiness/handoff/plan/preflight/next-action artifacts exist.
- Each JSON artifact has the expected schema version.
- Each JSON artifact's ready field is true.
- JSON artifacts with `ready_for_cutover` keep it false.
- Optional template JSON points at the same operator evidence Markdown.

## 7. Output Contract

The JSON and Markdown reports must include:

- `ready_for_archive`;
- `ready_for_cutover=false`;
- tenant ID, target schema, and redacted target URL;
- artifact count;
- per-artifact path, byte size, schema version, ready field, ready status, and
  SHA-256 digest;
- blockers.

## 8. Test Plan

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Also run py_compile and `git diff --check`.

## 9. Acceptance Criteria

- Green evidence chain produces `ready_for_archive=true`.
- Missing or stale artifacts block under `--strict`.
- SHA-256 digest is present for every archived artifact.
- The archive tool never connects to a database.
- `ready_for_cutover` remains false.
