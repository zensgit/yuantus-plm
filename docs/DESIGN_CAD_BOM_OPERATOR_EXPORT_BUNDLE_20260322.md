# CAD BOM Operator Export Bundle Design

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-bom-ops-bundle`

## Goal

Extend the existing CAD BOM recovery surface so operators can export one
evidence-grade bundle that captures the current CAD BOM state, review state,
history, and bounded recovery guidance.

This increment is intentionally narrow:

- add `GET /api/v1/cad/files/{file_id}/bom/export?export_format=zip|json`
- add a dedicated CAD BOM operations runbook
- keep raw artifact delivery unchanged

## Reference Anchors

- DocDoku import preview stays narrow and split across separate surfaces:
  - `references/docdoku-plm/docdoku-plm-front/app/product-management/js/views/part/part_importer.js`
  - `references/docdoku-plm/docdoku-plm-front/app/product-management/js/templates/part/part_import_form.html`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ImportPreviewDTO.java`
- DocDoku conversion/import diagnostics are richer in backend details than in
  operator surface:
  - `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/App.java`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-ext/src/main/java/com/docdoku/plm/server/importers/BomImporterResult.java`
- Odoo BOM compare provides coarse difference vocabulary but not one unified
  evidence bundle:
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/pack_and_go_wizard.py`

## Scope

### 1. `GET /api/v1/cad/files/{file_id}/bom/export`

Add a new export endpoint on the derived/operator CAD BOM surface.

Supported formats:

- `json`
- `zip`

The export payload includes:

- `file`
  - file id
  - filename
  - connector/format/document type
  - current review state/note
  - whether a stored CAD BOM artifact exists
- `cad_bom`
  - current derived BOM response
  - `summary`
  - `import_result`
  - `bom`
- `review`
  - current review state
- `history`
  - recent CAD change log entries
- `links`
  - structured BOM
  - raw BOM download
  - review
  - history
  - reimport
  - file metadata

ZIP contents are evidence-oriented:

- `bundle.json`
- `file.json`
- `summary.json`
- `review.json`
- `import_result.json`
- `bom.json`
- `history.json`
- `history.csv`
- `recovery_actions.csv`
- `issue_codes.csv`
- `README.txt`

### 2. Keep raw artifact contract unchanged

This increment does not change:

- `GET /api/v1/file/{file_id}/cad_bom`

That endpoint remains the raw/stored artifact surface. The new export lives on
the derived/operator path.

### 3. Add operator runbook

Add a dedicated runbook for:

- structured BOM inspection
- bundle export
- review lookup
- history lookup
- bounded reimport
- issue-code-driven triage

## Why This Surpasses Reference Detail

This is a detail and delivery improvement, not broader product scope.

- DocDoku has preview, viewer, and status surfaces, but they are fragmented.
  Yuantus now gives operators one exportable evidence surface tied directly to
  the live CAD BOM contract.
- Odoo has BOM diff vocabulary and zip-based export patterns, but not a single
  CAD BOM recovery bundle with review state, history, and recovery actions in
  one package.
- Yuantus turns current CAD BOM state into something that can be attached to
  incidents, regressions, and private deployment verification without forcing
  operators to reconstruct the situation manually.

## Non-Goals

- No BOM merge/apply wizard
- No change to the raw `/file/{file_id}/cad_bom` payload
- No connector schema rewrite
- No new background task type

## Files

- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`
- `docs/RUNBOOK_CAD_BOM_OPERATIONS.md`
- `docs/DESIGN_CAD_BOM_OPERATOR_EXPORT_BUNDLE_20260322.md`
- `docs/DEV_AND_VERIFICATION_CAD_BOM_OPERATOR_EXPORT_BUNDLE_20260322.md`
