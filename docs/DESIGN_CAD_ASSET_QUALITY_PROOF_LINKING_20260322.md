# CAD Asset Quality Proof Linking Design

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-asset-quality-proof-linking`

## Goal

Extend the current CAD operator surface so one file revision can answer one
bounded question through one proof-oriented contract:

- are the CAD assets trustworthy,
- is the viewer surface ready,
- does the derived CAD BOM drift from the live BOM,
- what review/history context already exists,
- and which recovery action should be taken next.

This increment does not try to build a new wizard. It links the existing
`asset_quality`, `viewer_readiness`, `cad_bom`, `mismatch`, `review`, and
`history` surfaces into one revision-centered proof ledger.

## Reference Anchors

- DocDoku keeps import preview, import status, conversion status, and linked
  document surfaces split across different API/DTO/UI layers:
  - `references/docdoku-plm/docdoku-plm-front/app/product-management/js/views/part/part_importer.js`
  - `references/docdoku-plm/docdoku-plm-front/app/product-management/js/templates/part/part_import_form.html`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/PartsResource.java`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ImportPreviewDTO.java`
  - `references/docdoku-plm/docdoku-plm-front/app/js/common-objects/views/part/conversion_status_view.js`
  - `references/docdoku-plm/docdoku-plm-front/app/js/common-objects/views/part/import_status_view.js`
  - `references/docdoku-plm/docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto/ConversionResultDTO.java`
- Odoo keeps operator proof split across separate heavy wizards:
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/pack_and_go_wizard.py`
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/plm_component.xml`
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom_view.xml`
- Current Yuantus anchors that this increment links together:
  - `src/yuantus/meta_engine/web/cad_router.py`
  - `src/yuantus/meta_engine/web/file_router.py`
  - `src/yuantus/meta_engine/services/cad_bom_import_service.py`
  - `src/yuantus/meta_engine/services/cad_converter_service.py`
  - `docs/DESIGN_CAD_ASSET_QUALITY_METADATA_20260322.md`
  - `docs/DESIGN_CAD_BOM_MISMATCH_PROOF_BUNDLE_20260322.md`

The benchmark gap is clear:

- DocDoku has rich backend proof, but front-end contract is mostly status-light
  oriented.
- Odoo has strong operator actions, but proof is fragmented into separate
  wizard flows.
- Yuantus can surpass both by keeping the current bounded APIs while also
  exposing one revision-centered proof surface that links trust, drift, review,
  and evidence export.

## Scope

### 1. Build one shared CAD operator proof bundle

Add one shared helper in `cad_router.py` that assembles:

- `file`
- `viewer_readiness`
- `asset_quality`
- `cad_bom`
- `operator_proof`
- `review`
- `history`
- `proof_manifest`
- `links`

This avoids duplicating proof assembly logic across endpoint and export paths.

### 2. Add `GET /api/v1/cad/files/{file_id}/proof`

Add a thin read-only endpoint that returns the shared operator proof bundle.

Stable proof fields:

- `bundle_version`
- `exported_at`
- `file`
- `viewer_readiness`
- `asset_quality`
- `cad_bom`
- `operator_proof`
- `review`
- `history`
- `proof_manifest`
- `links`

Stable proof statuses:

- `ready`
- `needs_review`
- `blocked`

Stable proof gap codes:

- `asset_quality_missing`
- `asset_quality_degraded`
- `converter_result_failed`
- `converter_result_degraded`
- `viewer_not_ready`
- `cad_bom_missing`
- `cad_bom_empty`
- `cad_bom_degraded`
- `cad_bom_live_mismatch`
- `cad_bom_mismatch_unresolved`
- `cad_review_pending`

### 3. Extend the existing CAD BOM export bundle instead of forking it

Keep `GET /api/v1/cad/files/{file_id}/bom/export` as the canonical export
surface, but extend it with linked proof files:

- `operator_proof.json`
- `viewer_readiness.json`
- `asset_quality.json`
- `asset_quality_issue_codes.csv`
- `asset_quality_recovery_actions.csv`

Also extend:

- `proof_manifest.json`
- `README.txt`

This keeps the export path stable while making the bundle truly revision-wide.

### 4. Link recovery guidance back to the unified proof surface

Update CAD BOM mismatch recovery guidance so drift-related recovery actions now
include:

- `open_cad_operator_proof_surface`

The existing mismatch surface stays available, but operator guidance should no
longer pretend that drift can be reviewed without asset-quality/viewer context.

### 5. Update the operator runbook

`docs/RUNBOOK_CAD_BOM_OPERATIONS.md` must now describe:

- when to read `/proof` before `/bom/mismatch`
- how to interpret `operator_proof.status`
- how to read `proof_gaps`
- which extra files exist in the export bundle

## Why This Surpasses Reference Detail

This is not broader scope. It is tighter proof discipline.

- DocDoku exposes rich conversion/import internals, but operators still move
  between separate status widgets and resources.
- Odoo gives operators heavy wizards, but pack/export and compare/diff do not
  converge on one revision-level proof object.
- Yuantus now links `asset_quality`, `viewer_readiness`, `BOM mismatch`,
  `review`, and `history` into one stable contract and one export bundle. That
  is stronger for private deployment verification because support, QA, and
  operators can inspect trust, drift, and next actions without stitching
  together multiple benchmark-style surfaces by hand.

## Non-Goals

- No new database model or migration
- No new CAD viewer UI page
- No BOM apply/merge flow
- No waiver/acknowledgement persistence in this batch
- No change to raw `/api/v1/file/{file_id}/cad_bom`

## Files

- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/services/cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_import_service.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
- `docs/RUNBOOK_CAD_BOM_OPERATIONS.md`
- `docs/DESIGN_CAD_ASSET_QUALITY_PROOF_LINKING_20260322.md`
- `docs/DEV_AND_VERIFICATION_CAD_ASSET_QUALITY_PROOF_LINKING_20260322.md`
