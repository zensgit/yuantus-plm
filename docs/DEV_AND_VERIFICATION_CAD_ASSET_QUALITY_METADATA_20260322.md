# CAD Asset Quality Metadata: Development & Verification

**Date**: 2026-03-22
**Branch**: `feature/codex-cad-asset-quality-metadata`

## Scope

This delivery extends the current CAD readiness/operator surface with:

- connector-backed `bbox/lod/result` metadata persistence
- `CADConverterService.assess_asset_quality(...)`
- `GET /api/v1/file/{file_id}/asset_quality`
- `asset_quality` inclusion in viewer readiness and consumer summary
- `asset_quality_status` and `asset_result_status` in readiness export
- connector schema/stub updates for `lods`, `result`, and `mesh_stats`

The raw artifact surface remains unchanged:

- `GET /api/v1/file/{file_id}/geometry`
- `GET /api/v1/file/{file_id}/cad_metadata`
- `GET /api/v1/file/{file_id}/cad_manifest`

## Implementation Notes

- the connector geometry branch in `cad_geometry(...)` now persists one JSON
  metadata artifact to `cad_metadata_path`
- the metadata payload is bounded and connector-agnostic:
  - `bbox`
  - `lods`
  - `mesh_stats`
  - `result`
- `assess_asset_quality(...)` now interprets both file presence and persisted
  converter metadata instead of relying on geometry existence alone
- converter-reported `degraded|failed` states now degrade the overall operator
  contract even when geometry files exist
- consumer-facing surfaces reuse the same `asset_quality` contract instead of
  inventing separate readiness-only status vocabularies
- connector schema and stub are updated together so local contract tests keep
  the integration boundary explicit

## Tests Added / Extended

### `src/yuantus/meta_engine/tests/test_cad_geometry_asset_quality_task.py`

- connector geometry conversion persists one `cad_metadata_path` payload
- persisted payload includes `bbox`, `lods`, `mesh_stats`, and `result`
- task response includes `cad_metadata_url`

### `src/yuantus/meta_engine/tests/test_file_viewer_readiness.py`

- `asset_quality` returns `ok` when geometry/metadata evidence is complete
- connector-shaped metadata with `lods` and degraded result is interpreted
  correctly
- `GET /asset_quality` returns the stable operator contract
- viewer readiness, consumer summary, and readiness export now surface
  `asset_quality`

### `src/yuantus/integrations/tests/test_contract_schemas.py`

- CAD connector convert schema accepts `artifacts.geometry.lods`
- CAD connector convert schema accepts `artifacts.result`
- CAD connector convert schema accepts `artifacts.mesh_stats`

### Existing targeted regression pack

- `src/yuantus/meta_engine/tests/test_cad_bom_task.py`
- `src/yuantus/meta_engine/tests/test_cad_bom_router.py`

These adjacent CAD operator tests remain important because this increment is
intended to strengthen the same readiness/proof surface, not fork it.

## Commands

Syntax:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-asset-quality-pycompile \
python3 -m py_compile \
  src/yuantus/meta_engine/services/cad_converter_service.py \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_cad_geometry_asset_quality_task.py \
  src/yuantus/integrations/tests/test_contract_schemas.py \
  services/cad-connector/app.py
```

Result:

- passed

Targeted:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-asset-quality-target \
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_cad_geometry_asset_quality_task.py \
  src/yuantus/integrations/tests/test_contract_schemas.py
```

Result:

- `36 passed, 2 warnings in 14.23s`

Doc contracts:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_core_required_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

- `5 passed in 0.11s`

Full stack:

```bash
PYTHONPYCACHEPREFIX=/tmp/yuantus-pyc-cad-asset-quality-full \
PYTEST_ADDOPTS='-p no:cacheprovider' \
scripts/verify_odoo18_plm_stack.sh full
```

Result:

- `739 passed, 253 warnings in 15.72s`

## Expected Operator Outcome

After this delivery, operators and integrators can:

1. tell whether CAD asset evidence is `ok|degraded|missing` without opening raw
   converter payloads
2. distinguish “geometry exists” from “converter result is trustworthy”
3. inspect persisted bbox/LOD/statistics evidence through one stable contract
4. reuse the same contract from file metadata, viewer readiness, consumer
   summary, and readiness export

That is the concrete operations/detail gain for this increment.
