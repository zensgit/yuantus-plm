# CAD 3D Connector Pipeline Integration (2026-01-27)

## Goal
Wire the DocDoku-style CAD connector service into Yuantus pipelines so that 3D files can:
- produce geometry/preview via external connector,
- extract attributes,
- import BOM structure into Part BOM relationships.

## Architecture
```
CAD Import → File stored (S3/local)
  ├─ cad_preview → CAD connector (preview)
  ├─ cad_geometry → CAD connector (geometry)
  ├─ cad_extract → CAD connector (attributes) → fallback extractor/local
  └─ cad_bom → CAD connector (bom) → BOM import → Part BOM
```

## Key Components
### 1) Connector Client
`src/yuantus/integrations/cad_connector.py`
- `/api/v1/convert` (file upload or file_url)
- `/health`, `/capabilities`
- Optional bearer token (`CAD_CONNECTOR_SERVICE_TOKEN`)

### 2) Pipeline Tasks
`src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `cad_preview`: prefers connector for 3D
- `cad_geometry`: prefers connector for 3D
- `cad_extract`: connector attributes (CadService)
- `cad_bom`: connector BOM → import

### 3) BOM Import Service
`src/yuantus/meta_engine/services/cad_bom_import_service.py`
- Maps connector BOM payload to Part + Part BOM
- Ensures root item exists
- Creates missing parts with minimal properties

### 4) API Surface
`/cad/import` new flag: `create_bom_job`
`/cad/files/{file_id}/bom` to read BOM results
`/file/{file_id}/cad_bom` to download BOM JSON

## Storage Layout
- Preview: `previews/{id[:2]}/{id}.png`
- Geometry: `geometry/{id[:2]}/{id}.gltf|glb|obj`
- BOM JSON: `cad_bom/{id[:2]}/{id}.json`

## Configuration
```
YUANTUS_CAD_CONNECTOR_BASE_URL=http://localhost:8300
YUANTUS_CAD_CONNECTOR_SERVICE_TOKEN=...
YUANTUS_CAD_CONNECTOR_MODE=optional|required
```

## Failure Modes
- Connector down → fallback to local conversion (unless mode=required)
- Empty BOM → import skipped
- Missing item_id → cad_bom job fails (must set item_id or auto_create_part)

## Verification
`scripts/verify_cad_connector_pipeline_3d.sh`

Expected: preview/geometry endpoints ready + BOM imported (>=1 line from stub)
