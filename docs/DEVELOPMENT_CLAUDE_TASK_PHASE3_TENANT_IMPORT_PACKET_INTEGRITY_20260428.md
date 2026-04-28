# Claude Task - Phase 3 Tenant Import Packet Integrity

Date: 2026-04-28

## 1. Goal

Harden the P3.4.2 importer implementation packet so it validates the upstream
artifact files referenced by next-action before it can say Claude may implement
the importer.

This remains a DB-free gate. It does not implement
`yuantus.scripts.tenant_import_rehearsal`.

## 2. Problem

The implementation packet already required a final green next-action report and
six upstream artifact paths. The missing safety check was that those paths could
be stale, missing, or point to reports that no longer contain green state.

## 3. Scope

- Validate every upstream artifact path exists.
- Read and validate each upstream JSON artifact.
- Require the expected schema version for:
  - P3.4.1 dry-run;
  - P3.4.2 readiness;
  - Claude handoff;
  - import plan;
  - source preflight;
  - target preflight.
- Require each artifact's ready field to be true.
- Require every artifact's blockers list to be empty.
- Require tenant and target schema consistency with next-action context.
- Add artifact-integrity rows to the generated Markdown packet.

## 4. Non-Goals

- No importer implementation.
- No source or target database connection.
- No row export or import.
- No schema creation, migration, downgrade, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 5. Expected Artifact Contracts

| Artifact | Schema | Ready field |
| --- | --- | --- |
| dry-run | `p3.4.1-dry-run-v1` | `ready_for_import` |
| readiness | `p3.4.2-import-rehearsal-readiness-v1` | `ready_for_rehearsal` |
| handoff | `p3.4.2-claude-import-rehearsal-handoff-v1` | `ready_for_claude` |
| plan | `p3.4.2-import-rehearsal-plan-v1` | `ready_for_importer` |
| source preflight | `p3.4.2-source-preflight-v1` | `ready_for_importer_source` |
| target preflight | `p3.4.2-target-preflight-v1` | `ready_for_importer_target` |

## 6. Acceptance

`ready_for_claude_importer=true` only when next-action is final and all six
artifact files exist, parse as JSON objects, match their expected schema,
contain the expected ready flag, have no blockers, and match tenant/schema
context.

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
