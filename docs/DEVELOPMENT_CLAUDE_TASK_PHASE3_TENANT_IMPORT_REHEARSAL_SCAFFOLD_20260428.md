# Claude Task - Phase 3 Tenant Import Rehearsal Scaffold

Date: 2026-04-28

## 1. Goal

Add the first `yuantus.scripts.tenant_import_rehearsal` entrypoint as a
fail-closed scaffold.

The scaffold validates the full implementation packet chain and emits JSON /
Markdown reports, but it deliberately stops before any database connection or
row import.

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal`.
- Require `--implementation-packet-json`.
- Require `--confirm-rehearsal` before the scaffold can pass.
- Validate implementation packet schema and `ready_for_claude_importer=true`.
- Re-run the fresh implementation-packet validation from next-action.
- Block if any upstream artifact is stale, missing, blocked, or mismatched.
- Emit JSON and Markdown scaffold reports.
- Keep:
  - `import_executed=false`;
  - `db_connection_attempted=false`;
  - `ready_for_cutover=false`.

## 3. Non-Goals

- No row export or import.
- No source or target database connection.
- No SQLAlchemy engine/session creation.
- No schema creation, migration, downgrade, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --output-json output/tenant_<tenant-id>_import_rehearsal_scaffold.json \
  --output-md output/tenant_<tenant-id>_import_rehearsal_scaffold.md \
  --confirm-rehearsal \
  --strict
```

## 5. Acceptance

The scaffold returns 0 in `--strict` mode only when:

- `--confirm-rehearsal` is present;
- implementation packet schema is current;
- implementation packet says `ready_for_claude_importer=true`;
- implementation packet says `ready_for_cutover=false`;
- implementation packet has no blockers;
- fresh packet validation from next-action is still green;
- implementation packet context matches fresh validation.

The scaffold must never claim that import was executed.

## 6. Report Shape

The JSON report includes:

- `schema_version`;
- `ready_for_rehearsal_scaffold`;
- `ready_for_import_execution` compatibility alias;
- `import_executed`;
- `db_connection_attempted`;
- `ready_for_cutover`;
- tenant/schema/context fields;
- upstream artifact paths;
- `fresh_artifact_validations`;
- `blockers`.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
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

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py

git diff --check
```
