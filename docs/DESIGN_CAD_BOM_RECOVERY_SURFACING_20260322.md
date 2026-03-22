# CAD BOM Recovery Surfacing Design

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-bom-recovery-surfacing`

## Goal

Extend the existing `cad_bom` contract work so operators and UI clients can
see three things without parsing free-form errors:

- whether the imported CAD BOM is ready or degraded,
- whether it needs operator review,
- how to request a bounded re-import using the existing job pipeline.

This increment intentionally avoids a new compare wizard or direct BOM editing
workflow. It stays on top of the current CAD import/review surfaces.

## Reference Anchors

- DocDoku import preview separates coarse operator-facing creation/checkout
  intent from the actual import flow:
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-ejb/src/main/java/com/docdoku/plm/server/ImporterBean.java`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ImportPreviewDTO.java`
- Odoo BOM compare uses coarse reason vocabulary such as `added` and
  `changed_qty`, which is easier for operators than raw internal details:
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`

The design borrows that shape: keep the detailed payload, but add a stable,
coarse summary layer.

## Scope

### 1. `GET /api/v1/cad/files/{file_id}/bom`

Add a derived `summary` block to `CadBomResponse`.

`summary` includes:

- `status`: `ready|degraded|empty|missing`
- `needs_operator_review`
- `issue_count`
- `issue_codes`
- `created_items`
- `existing_items`
- `created_lines`
- `skipped_lines`
- `error_count`
- `root`
- `root_source`
- `contract_status`
- `recovery_actions`

This keeps `import_result` and `bom` intact while giving UI/operator a stable
coarse surface.

### 2. Auto-review badge on partial/invalid import

The `cad_bom` task already writes the derived artifact and the `FileContainer`
already has:

- `cad_review_state`
- `cad_review_note`
- `cad_review_by_id`
- `cad_reviewed_at`

When BOM import is partial or invalid, the task now sets:

- `cad_review_state = "pending"`
- `cad_review_note = "CAD BOM import requires operator review"`
- clears reviewer identity/timestamp

This reuses the existing review badge instead of inventing a new workflow.

### 3. `POST /api/v1/cad/files/{file_id}/bom/reimport`

Add one bounded recovery action that reuses the existing async `cad_bom` job.

Item resolution order:

1. request body `item_id`
2. last stored CAD BOM wrapper `item_id`
3. single attached `ItemFile`

Failure modes:

- missing item resolution -> `400` with `code=cad_bom_reimport_item_missing`
- multiple attached items -> `400` with `code=cad_bom_reimport_item_ambiguous`

On success:

- enqueue `cad_bom` with the same job payload shape used by CAD import
- log `cad_bom_reimport_requested` in CAD history
- return `file_id`, `item_id`, `job_id`, `job_status`

## Why This Surpasses Reference Detail

This is not broader product scope. It is better operational detail:

- DocDoku preview is conceptually separate, but Yuantus now exposes a stable
  summary directly on the live CAD BOM response.
- Odoo exposes coarse reasons inside its wizard flow; Yuantus now exposes
  coarse issue codes on an API contract that frontends and runbooks can reuse.
- The existing file review badge becomes an automatic signal for partial/invalid
  CAD BOM imports, which is stronger for private deployment operations than
  relying on logs or raw JSON alone.

## Non-Goals

- No new BOM compare UI
- No in-place BOM line patch endpoint
- No connector schema rewrite
- No raw `/api/v1/file/{file_id}/cad_bom` contract change

## Files

- `src/yuantus/meta_engine/services/cad_bom_import_service.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_task.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
