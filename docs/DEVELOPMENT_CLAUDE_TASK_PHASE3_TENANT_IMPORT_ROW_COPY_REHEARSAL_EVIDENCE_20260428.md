# Development Task - Phase 3 Tenant Import Row-Copy Rehearsal Evidence

Date: 2026-04-28

## 1. Goal

Add a DB-free evidence gate after the P3.4.2 row-copy rehearsal.

The gate validates that a non-production rehearsal report, its implementation
packet, and the operator sign-off Markdown are internally consistent and safe to
archive.

## 2. Scope

- Add `src/yuantus/scripts/tenant_import_rehearsal_evidence.py`.
- Add focused tests in `src/yuantus/tests/test_tenant_import_rehearsal_evidence.py`.
- Update `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- Update tenant import TODOs and `docs/DELIVERY_DOC_INDEX.md`.
- Add this taskbook plus a DEV/verification record and TODO MD.

## 3. Non-Goals

- No database connections.
- No row-copy execution.
- No schema creation, migration, downgrade, truncate, cleanup, or rollback.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No approval to import global/control-plane tables.

## 4. CLI Shape

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --operator-evidence-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --output-json output/tenant_<tenant-id>_import_rehearsal_evidence.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_evidence.md \
  --strict
```

## 5. Required Validations

- Rehearsal report schema is `p3.4.2-tenant-import-rehearsal-v1`.
- Rehearsal report has `ready_for_rehearsal_import=true`.
- Rehearsal report has `import_executed=true`.
- Rehearsal report has `db_connection_attempted=true`.
- Rehearsal report has `ready_for_cutover=false`.
- Rehearsal report has no blockers.
- Implementation packet schema is the current importer packet schema.
- Implementation packet has `ready_for_claude_importer=true`.
- Implementation packet has `ready_for_cutover=false`.
- Implementation packet tenant, schema, and target URL match the rehearsal report.
- Implementation packet is fresh-revalidated from `next_action_json`.
- Fresh upstream dry-run, readiness, handoff, plan, source preflight, and target
  preflight artifacts still exist and remain green.
- Table results are non-empty, unique by table name, and contain no global/control-plane table.
- Every table result has integer expected/inserted counts and `row_count_matches=true`.
- Operator evidence has a complete `## Rehearsal Evidence Sign-Off` block.
- Operator tenant and rehearsal DB match the rehearsal report.
- Operator result is an accepted pass value.

## 6. Output Contract

The JSON and Markdown reports must include:

- `ready_for_rehearsal_evidence`
- `operator_rehearsal_evidence_accepted`
- `ready_for_cutover=false`
- redacted target URL
- table-level row results
- operator sign-off summary
- blockers

## 7. Test Plan

```bash
.venv/bin/python -m pytest -q \
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

Also run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py

git diff --check
```

## 8. Acceptance Criteria

- The evidence CLI is fail-closed and exits non-zero under `--strict` when blocked.
- Reports never expose source or target database secrets.
- `ready_for_cutover` remains false in all paths.
- The runbook shows the operator evidence template and command.
- Focused regression, doc-index contracts, py_compile, and diff check pass.
