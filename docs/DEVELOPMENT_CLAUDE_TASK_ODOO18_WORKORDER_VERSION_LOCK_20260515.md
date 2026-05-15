# Claude Taskbook: Odoo18 Workorder Version Lock R1

Date: 2026-05-15

## 1. Purpose

Implement the first runtime slice for the highest-priority Odoo18 R2 gap:
`mrp_workorder_plm` style workorder document version locking.

The goal is narrow: when a routing or operation document is attached to a
workorder document package, the package can carry an explicit document version
pointer and can fail closed when production export requires locked versions.

This taskbook is implementation-facing. It is intended for Claude Code or an
equivalent implementation worker after the R2 analysis PR and this taskbook PR
are accepted.

## 2. Current Baseline

R2 analysis source:

- `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`

Code evidence:

- `src/yuantus/meta_engine/web/parallel_tasks_workorder_docs_router.py`
  exposes:
  - `POST /workorder-docs/links`
  - `GET /workorder-docs/links`
  - `GET /workorder-docs/export`
- `src/yuantus/meta_engine/models/parallel_tasks.py` defines
  `WorkorderDocumentLink` with:
  - `routing_id`
  - `operation_id`
  - `document_item_id`
  - `inherit_to_children`
  - `visible_in_production`
  - no version pointer
- `src/yuantus/meta_engine/manufacturing/models.py` defines `Operation` with
  `document_ids`, but no locked version metadata.
- `src/yuantus/meta_engine/services/parallel_tasks_service.py` has
  `WorkorderDocumentPackService.upsert_link`, `list_links`, and `export_pack`.
- `src/yuantus/meta_engine/services/eco_service.py` applies ECO target versions
  in `action_apply` and already calls `VersionFileService.sync_version_files_to_item`.
- `src/yuantus/meta_engine/version/models.py` has `ItemVersion` and
  `VersionFile`, which are the existing source of version/file truth.
- `migrations/versions/z1b2c3d4e7a5_add_parallel_branch_tables.py` and
  `migrations_tenant/versions/t1_initial_tenant_baseline.py` already create
  `meta_workorder_document_links`, so schema changes must update both main and
  tenant migration surfaces.

## 3. R1 Target Output

Deliver one bounded implementation PR:

- Add explicit `document_version_id` support to workorder document links.
- Preserve backward compatibility for existing links without a version pointer.
- Include version-lock metadata in list and export responses.
- Add an opt-in production export guard that rejects unlocked or stale links.
- Add a minimal ECO apply projection hook for direct product/document item links.
- Add migrations, tests, and a development/verification MD.

## 4. Data Model

Add fields to `WorkorderDocumentLink`:

- `document_version_id: Optional[str]`
- `version_locked_at: Optional[datetime]`
- `version_lock_source: Optional[str]`

Recommended semantics:

- `document_version_id` references `meta_item_versions.id`.
- The referenced version must belong to `document_item_id`.
- Existing unique constraint remains
  `(routing_id, operation_id, document_item_id)` so upsert updates the active
  link instead of creating multiple active rows for multiple versions.
- `version_lock_source` is one of:
  - `manual`
  - `eco_apply`
  - `backfill`
- Backward compatibility: existing rows remain valid with
  `document_version_id = NULL`.

Migration requirements:

- Add a main Alembic migration under `migrations/versions/`.
- Update tenant baseline through the existing tenant-baseline generator path
  when applicable; do not hand-edit generated baseline output unless the repo's
  current process requires it.
- Add or update migration coverage contracts if the existing migration coverage
  suite flags the new columns/indexes.

## 5. Service Behavior

Extend `WorkorderDocumentPackService`.

### 5.1 Upsert

`upsert_link` accepts:

- `document_version_id: Optional[str] = None`
- `version_lock_source: str = "manual"`

Validation:

- If `document_version_id` is provided, load `ItemVersion`.
- Reject missing version with `ValueError`.
- Reject version whose `item_id` does not equal `document_item_id`.
- Set `version_locked_at` when a version is provided.
- Preserve existing `inherit_to_children` and `visible_in_production` behavior.

### 5.2 List

`list_links` remains shape-compatible but returned rows must allow callers to
serialize:

- `document_version_id`
- `version_locked`
- `version_lock_source`
- `version_locked_at`
- `version_is_current`
- `version_is_released`
- `version_label`

These metadata fields may be computed in a small serializer helper rather than
attached to the ORM model.

### 5.3 Export

`export_pack` accepts:

- `require_locked_versions: bool = False`

When `require_locked_versions` is false:

- Existing export behavior remains compatible.
- Manifest and CSV include version-lock fields.
- Unlocked rows are reported in `version_lock_summary`.

When `require_locked_versions` is true:

- Reject any production-visible row with no `document_version_id`.
- Reject any row whose `document_version_id` no longer belongs to
  `document_item_id`.
- Reject stale rows only if the task implements `version_is_current` freshness
  checking in this R1. If freshness checking is deferred, document that and
  guard only missing/mismatched locks.

Recommended manifest additions:

```json
{
  "version_lock_summary": {
    "locked": 2,
    "unlocked": 0,
    "stale": 0,
    "requires_lock": true
  }
}
```

## 6. API Surface

Update `WorkorderDocLinkRequest` in
`parallel_tasks_workorder_docs_router.py`:

- `document_version_id: Optional[str] = None`

Update `POST /workorder-docs/links` response:

- Include the version-lock fields listed in §5.2.

Update `GET /workorder-docs/links` response:

- Include the version-lock fields for every link row.

Update `GET /workorder-docs/export` query:

- `require_locked_versions: bool = Query(False)`

Do not add new routes in R1 unless the implementation proves a diagnostics
endpoint is strictly necessary. Prefer additive fields on the existing three
routes.

## 7. ECO Apply Projection

Add a minimal, explicit hook after ECO apply switches the product current
version and syncs version files:

```text
ECOService.action_apply(...)
  -> WorkorderDocumentPackService.refresh_document_version_locks_for_item(
       document_item_id=product.id,
       document_version_id=target_version.id,
       source="eco_apply",
     )
```

Strict boundary:

- Only update `WorkorderDocumentLink` rows whose `document_item_id` exactly
  matches the ECO product/document item.
- Do not infer unrelated document items from BOM lines, routing operations, or
  file attachments in R1.
- Do not create new workorder document links from ECO apply.
- Do not implement a full MES workorder instance domain.

If direct product/document item matching is not sufficient after implementation
inspection, keep the service method but call it only from tests or defer the ECO
hook with a documented reason. Do not build a broad inference layer.

## 8. Tests Required

Add or update focused tests.

Service tests in `test_parallel_tasks_services.py`:

- Upsert with `document_version_id` persists lock metadata.
- Upsert rejects missing version.
- Upsert rejects version belonging to another item.
- List returns operation-specific and inherited links with version metadata.
- Export manifest and CSV include version-lock fields.
- Export with `require_locked_versions=True` rejects an unlocked visible link.
- Export with `require_locked_versions=True` accepts locked inherited and
  operation links.

Router tests:

- `POST /workorder-docs/links` accepts `document_version_id` and returns it.
- `GET /workorder-docs/export?require_locked_versions=true` passes the flag to
  service or exercises the real service path.
- Existing route ownership contract still passes and route count remains
  unchanged.

ECO tests:

- `action_apply` calls the workorder-doc lock refresh hook after target version
  apply.
- Hook failure policy is explicit:
  - either fail the ECO apply with `ValueError` if lock refresh is mandatory;
  - or log/collect warning if best-effort.
- Prefer fail-closed for production lock correctness unless a reviewer accepts
  best-effort semantics.

Migration tests:

- Main migration adds `document_version_id`.
- Tenant baseline includes the new column/index if tenant baseline is updated.
- Doc-index trio remains green for the new DEV/verification MD.

## 9. Verification Commands

Use the repo virtualenv when available:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_workorder_docs_router_contracts.py
```

```bash
.venv/bin/python -m pytest -q \
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

If tenant baseline output changes, also run the repo's tenant baseline generator
check, for example:

```bash
.venv/bin/python scripts/generate_tenant_baseline.py --check
```

Adjust only if the script name or invocation has changed.

## 10. Non-Goals

- No full MES workorder-instance domain.
- No Gantt, scheduling, barcode, IoT, or real-time labor reporting.
- No quality gate enforcement; that is a separate R2 priority.
- No pack-and-go mainline migration.
- No BOM archive endpoint.
- No automatic inference from BOM/routing trees to document links.
- No data migration that guesses versions for existing links.
- No production setting flip that forces all exports to require locks by
  default.

## 11. Claude Code Handoff

Claude Code should own the implementation PR after explicit opt-in.

Suggested branch:

`feat/odoo18-workorder-version-lock-r1-20260515`

Claude Code should:

- Read this taskbook and `docs/DEVELOPMENT_ODOO18_GAP_ANALYSIS_20260514.md`.
- Implement only R1 scope.
- Add the implementation DEV/verification MD.
- Keep `.claude/` and `local-dev-env/` out of git.
- Stop and report if schema generation or ECO projection semantics are unclear.

Codex review should:

- Verify the API remains backward compatible by default.
- Verify version ownership validation.
- Verify export fail-closed behavior when `require_locked_versions=true`.
- Verify migration and tenant-baseline consistency.
- Verify no MES/quality/pack-and-go scope creep.
