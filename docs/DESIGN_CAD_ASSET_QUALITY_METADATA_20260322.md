# CAD Asset Quality Metadata Design

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-asset-quality-metadata`

## Goal

Extend the current CAD conversion/readiness surface so operators and integrators
can answer one bounded question without opening raw converter output or
guessing from file presence alone:

- are the derived CAD assets structurally usable,
- did the converter report `ok|degraded|failed`,
- which bbox/LOD/statistics evidence was persisted,
- and which follow-up surface should be opened next.

This increment stays narrow:

- persist connector-backed `bbox/lod/result` metadata
- expose one stable `asset_quality` contract
- surface that contract through existing file/readiness endpoints
- keep raw CAD artifact delivery unchanged

## Reference Anchors

- DocDoku conversion service computes geometry metadata such as bounding box and
  LOD outputs as part of the conversion pipeline:
  - `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/App.java`
  - `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/ConversionResultDozerConverter.java`
  - `references/docdoku-plm/docdoku-plm-conversion-service/conversion-service/src/main/java/com/docdoku/plm/conversion/service/Decimater.java`
- Odoo compare/export references show proof-oriented operator patterns, but not
  a unified CAD asset quality surface:
  - `references/odoo18-enterprise-main/addons/plm_compare_bom/wizard/compare_bom.py`
  - `references/odoo18-enterprise-main/addons/plm_pack_and_go/wizard/pack_and_go_wizard.py`
- Current Yuantus anchors that this increment extends:
  - `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
  - `src/yuantus/meta_engine/services/cad_converter_service.py`
  - `src/yuantus/meta_engine/web/file_router.py`
  - `docs/DEVELOPMENT_DIRECTION_OPERATIONS_DETAIL_SURPASS_20260321.md`
  - `docs/REFERENCE_GROUNDED_SURPASS_BACKLOG_20260321.md`

The design deliberately goes beyond reference behavior in one specific way:
DocDoku computes rich conversion-side metadata, but Yuantus persists it into a
stable operator contract that is easy to inspect from API responses, readiness
exports, and downstream evidence bundles.

## Scope

### 1. Persist connector-backed `bbox/lod/result` metadata

Extend the 3D connector branch in `cad_geometry(...)` so successful geometry
downloads also persist one JSON metadata artifact to `cad_metadata_path`.

Persisted fields:

- `kind`
- `source`
- `file_id`
- `bbox`
- `lods`
- `mesh_stats`
  - `triangle_count`
  - `entity_count`
- `result`
  - `status`
  - `error_output`
  - `warnings`

This keeps metadata storage aligned with the existing `cad_metadata_path`
pattern instead of adding a new table or route family.

### 2. Build one stable operator-facing `asset_quality` contract

Add `assess_asset_quality(...)` to `CADConverterService`.

Stable top-level fields:

- `status`
- `result_status`
- `geometry_format`
- `schema_version`
- `result`
- `bbox`
- `bbox_source`
- `triangle_count`
- `entity_count`
- `lod`
- `proof_files`
- `issue_codes`
- `recovery_actions`
- `links`

Stable statuses:

- `ok`
- `degraded`
- `missing`

Stable completeness states:

- `complete`
- `partial`
- `missing`

Important operator rule:

- file presence alone is not enough for `ok`
- if converter result is `degraded`, overall `asset_quality.status` must also
  degrade even when geometry and metadata files exist
- if converter result is `failed`, the operator surface must fall to `missing`

This makes the contract safer than simple “artifact exists” heuristics.

### 3. Expose the contract through bounded file/readiness surfaces

Add `GET /api/v1/file/{file_id}/asset_quality`.

The endpoint returns the stable `asset_quality` contract plus:

- `file_id`
- `filename`
- `document_type`
- `cad_format`
- `cad_connector_id`

Also extend existing bounded surfaces:

- `GET /api/v1/file/{file_id}/viewer_readiness`
  - include nested `asset_quality`
- `GET /api/v1/file/{file_id}/consumer-summary`
  - include `asset_quality`
  - include `urls.asset_quality`
- `POST /api/v1/file/viewer-readiness/export`
  - include `asset_quality_status`
  - include `asset_result_status`

This keeps `asset_quality` close to the operator/consumer surfaces that already
exist instead of creating a detached diagnostic API family.

### 4. Extend the CAD connector contract and stub

Extend `contracts/cad_connector_convert.schema.json` and the local connector
stub so connector-backed 3D responses may declare:

- `artifacts.geometry.lods`
- `artifacts.result`
- `artifacts.mesh_stats`

This preserves backward compatibility while making the expected metadata
explicit for connector integrations and contract tests.

### 5. Keep raw artifact delivery unchanged

This increment does not change:

- `GET /api/v1/file/{file_id}/geometry`
- `GET /api/v1/file/{file_id}/cad_metadata`
- `GET /api/v1/file/{file_id}/cad_manifest`
- `GET /api/v1/file/{file_id}/cad_bom`

It also does not add:

- a new DB model
- a new background task type
- UI rendering logic
- CAD BOM mismatch/proof linkage in the same batch

## Why This Surpasses Reference Detail

This is not a broader feature claim. It is a better operational contract.

- DocDoku already has converter-side bbox/LOD logic, but the operator still has
  to reconstruct whether the current asset set is trustworthy from multiple
  backend/UI surfaces.
- Odoo gives proof/export patterns, but not a CAD asset-quality contract tied to
  geometry readiness and converter result semantics.
- Yuantus now persists `bbox/lod/result` into one stable contract and exposes it
  directly through file/readiness surfaces. That is stronger for private
  deployments because operator, support, and UI clients can answer “is this CAD
  asset set usable and why” without replaying conversion internals by hand.

## Non-Goals

- No CAD viewer UI change
- No new proof zip/export bundle in this batch
- No BOM mismatch linkage in this batch
- No connector callback job orchestration rewrite
- No migration or new persistent SQL column

## Files

- `contracts/cad_connector_convert.schema.json`
- `services/cad-connector/app.py`
- `src/yuantus/integrations/tests/test_contract_schemas.py`
- `src/yuantus/meta_engine/services/cad_converter_service.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_cad_geometry_asset_quality_task.py`
- `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`
- `docs/DESIGN_CAD_ASSET_QUALITY_METADATA_20260322.md`
- `docs/DEV_AND_VERIFICATION_CAD_ASSET_QUALITY_METADATA_20260322.md`
