# Odoo18 Workorder Version-Lock R1 — Development and Verification

Date: 2026-05-15

## 1. Goal

Implement the first runtime slice of the highest-priority Odoo18 R2 gap
identified in `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`:
`mrp_workorder_plm` style **workorder document version locking**.

Concretely, R1 adds:

- An explicit `document_version_id` pointer on `meta_workorder_document_links`.
- A version-ownership invariant: a linked version must belong to its
  `document_item_id`.
- Service + router surface to set, read, and (optionally) require locked
  versions during production export.
- A minimal ECO apply projection so that when an ECO promotes a target
  version on a product, every existing workorder-doc link for that
  product re-points to the new version (no inference, no new links).
- A main alembic migration plus a regenerated tenant baseline so the
  schema lands in both runtime paths.

R1 is **default off** — `require_locked_versions` defaults to `false`, existing
upserts without a `document_version_id` remain valid, and unlocked links
continue to flow through the existing export path.

## 2. Scope

### Modified

- `src/yuantus/meta_engine/models/parallel_tasks.py`
- `src/yuantus/meta_engine/services/parallel_tasks_service.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py`
- `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
- `migrations_tenant/versions/t1_initial_tenant_baseline.py`
  (regenerated via `scripts/generate_tenant_baseline.py`)
- `docs/DELIVERY_DOC_INDEX.md`

### Added

- `migrations/versions/aa1b2c3d4e7b0_add_workorder_doc_version_lock.py`
- `docs/DEV_AND_VERIFICATION_ODOO18_WORKORDER_VERSION_LOCK_R1_20260515.md`

## 3. Data Model Changes

`WorkorderDocumentLink` gains three nullable fields:

| Column | Type | Notes |
|---|---|---|
| `document_version_id` | `String`, indexed | References `meta_item_versions.id`; nullable for backward compatibility |
| `version_locked_at` | `DateTime` | Set when a lock is applied; cleared when caller passes `document_version_id=None` |
| `version_lock_source` | `String(40)` | One of `manual` / `eco_apply` / `backfill` |

The existing unique constraint
`uq_workorder_doc_link_scope(routing_id, operation_id, document_item_id)`
is **unchanged** — upsert still updates a single active row per scope rather
than creating multiple rows for multiple versions of the same document.

## 4. Service Behavior

### 4.1 `WorkorderDocumentPackService.upsert_link`

New optional arguments:

- `document_version_id: Optional[str] = None`
- `version_lock_source: str = "manual"` (must be one of the allowed source
  literals; defaults applied when caller passes the raw value)

Validation, fail-closed:

- `document_version_id` must resolve to an `ItemVersion`. Missing → `ValueError`.
- The resolved version's `item_id` must equal the link's `document_item_id`.
  Mismatch → `ValueError`.
- `version_lock_source` must be in the allowed set. Unknown → `ValueError`.

When `document_version_id` is set, `version_locked_at` and `version_lock_source`
are written. When `document_version_id` is `None`, all three columns are
cleared together — there is no "lock half-applied" state.

### 4.2 `WorkorderDocumentPackService.list_links`

Signature unchanged. Callers serialize via the new
`WorkorderDocumentPackService.serialize_link(link)` helper which produces a
dict with the legacy keys plus:

- `document_version_id`
- `version_locked` (boolean derived from `document_version_id`)
- `version_lock_source`
- `version_locked_at` (ISO string)
- `version_label`
- `version_is_current`
- `version_is_released`
- `version_belongs_to_item`

The helper is the single source of truth for the API response shape; ORM rows
themselves carry only the column values.

### 4.3 `WorkorderDocumentPackService.export_pack`

New optional argument:

- `require_locked_versions: bool = False`

The manifest gains a `version_lock_summary` block with the following keys
(based only on the visible/production rows in scope):

```json
{
  "version_lock_summary": {
    "locked": 2,
    "unlocked": 0,
    "mismatched": 0,
    "stale": 0,
    "requires_lock": true
  }
}
```

Per-doc rows in `manifest["documents"]` (and `documents.csv`) carry the same
version-lock fields as the list response.

Fail-closed behavior when `require_locked_versions=True`:

- Any visible row with no `document_version_id` → `ValueError`.
- Any visible row whose linked version no longer belongs to its
  `document_item_id` → `ValueError`.
- **Stale rows** (linked version with `is_current=False`) are surfaced in
  `version_lock_summary.stale` but do not raise. Freshness rejection is
  deferred per taskbook §5.3 because the `is_current` signal can lag in
  active edit flows; explicit re-lock via the ECO apply hook (§4.4) is the
  authoritative refresh mechanism in R1.

### 4.4 `WorkorderDocumentPackService.refresh_document_version_locks_for_item`

New method, narrow contract:

- Validates the supplied `document_version_id` against the supplied
  `document_item_id` (same invariant as upsert).
- Re-points every `WorkorderDocumentLink` row whose
  `document_item_id` exactly matches the input.
- **Does not create new rows.** Does not touch rows for other items.
- Returns the count of rows updated.
- Rows already pointing at the target `document_version_id` are skipped:
  `version_lock_source` and `version_locked_at` are **not** rewritten to
  `eco_apply` / `now()` for those rows. This preserves prior `manual` lock
  provenance on no-op re-applies.

## 5. ECO Apply Projection

`ECOService.action_apply` calls
`WorkorderDocumentPackService.refresh_document_version_locks_for_item(...)`
immediately after `VersionFileService.sync_version_files_to_item(...)`. The
call uses `product.id` and `target_version.id` directly — there is no
inference layer that walks BOM lines, routing operations, or attachment
trees.

Hook failure is **fail-closed**: if the refresh raises `ValueError`,
`action_apply` re-raises with a wrapping message:

```text
ValueError("workorder document version-lock refresh failed: <original>")
```

This is the production-safe default. If a future revision needs best-effort
semantics, that should be its own explicit opt-in.

## 6. API Surface

- `POST /api/v1/workorder-docs/links` accepts an optional
  `document_version_id` in the request body and returns the full serialized
  link (including version-lock metadata) on success.
- `GET /api/v1/workorder-docs/links` returns the full serialized shape for
  every link row.
- `GET /api/v1/workorder-docs/export?require_locked_versions=true` rejects
  unlocked/mismatched rows with a `409 workorder_export_unlocked_versions`
  response containing the offending link ids in the error context.
  Default (`require_locked_versions=false`) is a backward-compatible export.

No new routes were added; R1 only adds additive fields and one optional
query parameter to the existing three routes.

## 7. Migration

Main migration: `migrations/versions/aa1b2c3d4e7b0_add_workorder_doc_version_lock.py`,
revision `aa1b2c3d4e7b0`, down-revision `z1b2c3d4e7a5`. Adds the three
columns and the `ix_meta_workorder_document_links_document_version_id`
index. The upgrade is idempotent (checks for existing columns and indexes).
Downgrade drops the index and the three columns.

Tenant baseline: `migrations_tenant/versions/t1_initial_tenant_baseline.py`
was regenerated by
`PYTHONPATH=src .venv/bin/python scripts/generate_tenant_baseline.py`.
The deterministic check
(`scripts/generate_tenant_baseline.py --check`) is green after the
regeneration.

## 8. Test Matrix

### Service tests
(`src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`)

- `test_workorder_doc_pack_upsert_persists_version_lock_metadata`
- `test_workorder_doc_pack_upsert_rejects_missing_version`
- `test_workorder_doc_pack_upsert_rejects_cross_item_version`
- `test_workorder_doc_pack_upsert_rejects_unknown_lock_source`
- `test_workorder_doc_pack_list_serializes_version_metadata`
- `test_workorder_doc_pack_export_manifest_includes_lock_summary`
- `test_workorder_doc_pack_export_require_locked_versions_fail_closed`
- `test_workorder_doc_pack_export_require_locked_versions_accepts_all_locked`
- `test_workorder_doc_pack_export_marks_stale_without_failing_closed`
- `test_workorder_doc_pack_refresh_updates_only_matching_item`
- `test_workorder_doc_pack_refresh_rejects_cross_item_version`

Plus the legacy
`test_workorder_doc_pack_supports_inherited_links_and_zip_export` and
`test_workorder_doc_pack_includes_locale_profile_context` tests continue to
pass — backward compatibility is preserved.

### ECO hook tests
(`src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`)

- `test_action_apply_runs_activity_gate_and_custom_actions_hooks` was
  extended to assert
  `WorkorderDocumentPackService.refresh_document_version_locks_for_item`
  is called once with `document_item_id`, `document_version_id`, and
  `source="eco_apply"`.
- `test_action_apply_fails_closed_on_workorder_doc_version_lock_refresh_error`
  asserts the wrapping `ValueError` is raised when the hook raises.

### Router contract tests
(`src/yuantus/meta_engine/tests/test_parallel_tasks_workorder_docs_router_contracts.py`)

Unchanged — route count and ownership invariants remain green. The new
`require_locked_versions` query parameter is additive, so route shape is
preserved.

## 9. Verification Commands

```bash
PYTHONPATH=src .venv/bin/python scripts/generate_tenant_baseline.py --check
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_workorder_docs_router_contracts.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/models/parallel_tasks.py \
  src/yuantus/meta_engine/services/parallel_tasks_service.py \
  src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py \
  src/yuantus/meta_engine/services/eco_service.py
```

```bash
git diff --check
```

## 10. Out of Scope (Reaffirmation)

Per taskbook §10 and per the implementation opt-in, R1 does **not** include:

- A full MES workorder-instance domain.
- Gantt, scheduling, barcode, IoT, or labor reporting.
- A quality gate on workorder steps (a separate R2 priority).
- Pack-and-go mainline migration.
- A `bom_archive` endpoint.
- Automatic inference from BOM/routing trees to document links.
- Data migration that guesses versions for existing links.
- Any production setting flip that forces all exports to require locks by
  default.

## 11. Follow-ups (Tracked, not implemented in R1)

- Decide whether to surface stale lock signals (visible version with
  `is_current=False`) as a soft warning header on the export route.
- Decide whether to add an explicit `/workorder-docs/lock-diagnostics`
  read-only endpoint (taskbook §6 explicitly discouraged adding new
  routes in R1).
- Confirm with PMM whether `require_locked_versions=true` should ever
  become the production default. This requires a separate opt-in PR with
  its own taskbook.
