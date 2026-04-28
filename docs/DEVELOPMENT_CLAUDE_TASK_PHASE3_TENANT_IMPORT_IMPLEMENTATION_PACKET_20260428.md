# Claude Task - Phase 3 Tenant Import Implementation Packet

Date: 2026-04-28

## 1. Goal

Add a DB-free final implementation packet for P3.4.2 tenant import rehearsal.

The packet converts a green next-action report into a bounded Claude task for
the future importer implementation.

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_implementation_packet`.
- Consume the P3.4.2 next-action JSON report.
- Require:
  - next-action schema `p3.4.2-import-rehearsal-next-action-v1`;
  - `next_action=ask_claude_to_implement_importer`;
  - `claude_required=true`;
  - empty next-action blockers;
  - dry-run, readiness, handoff, plan, source preflight, and target preflight
    artifact paths.
- Emit JSON and Markdown implementation packets.
- Keep `ready_for_cutover=false`.

## 3. Non-Goals

- No importer implementation.
- No database connections.
- No row export or import.
- No schema creation, migration, downgrade, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_implementation_packet \
  --next-action-json output/tenant_<tenant-id>_import_rehearsal_next_action.json \
  --output-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --output-md output/tenant_<tenant-id>_claude_importer_task.md \
  --strict
```

## 5. Acceptance

`ready_for_claude_importer=true` only when the next-action report is in the
final state:

```text
claude_required=true
next_action=ask_claude_to_implement_importer
```

The packet must also include all upstream evidence paths:

- dry-run JSON;
- readiness JSON;
- handoff JSON;
- plan JSON;
- source preflight JSON;
- target preflight JSON.

## 6. Claude Boundary

Claude should implement `yuantus.scripts.tenant_import_rehearsal` only from a
packet Markdown whose header says:

```text
Claude can implement importer: `true`
```

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
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
  src/yuantus/scripts/tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py

git diff --check
```
