# CAD 3D Connector Plugin Design (2026-01-27)

## Goal
Provide a **real 3D connector plugin** architecture (Creo/NX/SolidWorks/CATIA/Inventor) that is decoupled from PLM core but integrates with Yuantus CAD pipelines for:
- **3D geometry + preview**
- **BOM extraction (assemblies)**
- **Attribute extraction (part metadata)**

This design builds on the existing connector contract and stub service.

## Current Baseline (in repo)
- Connector contract (DocDoku-style): `docs/DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`
- Stub service (FastAPI): `services/cad-connector/`
- Local 3D connector verification: `scripts/verify_cad_connectors_3d.sh`
- Stub verification: `scripts/verify_cad_connector_stub.sh`
- CAD pipelines: `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- CAD attribute extraction: `src/yuantus/meta_engine/services/cad_service.py`

## Design Choice
**Adopt a DocDoku-style conversion microservice (plugin host)** and integrate it via HTTP.
- Avoids embedding vendor SDKs inside the PLM stack
- Supports Windows-hosted connectors + licenses
- Allows incremental onboarding per CAD format

## Architecture
```
Yuantus API/Worker
  ├─ CAD import → store file (S3/local)
  ├─ enqueue jobs: preview / geometry / bom / extract
  └─ call CAD Connector (HTTP)
           ↓
  CAD Connector Plugin Host (Windows-friendly)
  ├─ format-based router
  ├─ vendor plugins (Creo/NX/SW/CATIA/Inventor)
  └─ outputs: glTF/PNG/BOM/attributes
```

## Plugin Contract (Recap)
See `docs/DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`. Required endpoints:
- `GET /health`
- `GET /capabilities`
- `POST /convert` (mode=extract|geometry|preview|bom|all)
- `GET /jobs/{id}` (async)

### Expected Artifacts
- geometry: glTF/GLB (optionally bin)
- preview: PNG/JPG
- bom: nodes/edges (assembly tree)
- attributes: part_number, revision, material, weight, etc.

## Integration Points (Yuantus)
### 1) CAD Import (API)
- `POST /api/v1/cad/import`
- Stores file, resolves `cad_format` + `cad_connector_id`
- Creates optional jobs (preview/geometry/bom)

### 2) CAD Pipeline (Worker)
- `cad_pipeline_tasks.py`
- For each job, call connector:
  - **file_url** (signed, preferred for large files)
  - **mode** = geometry / preview / bom / extract

### 3) Attribute Extraction
- Current flow uses `CadExtractorClient` → local fallback.
- Add **CadConnectorClient** (new) for 3D plugins.
- Fallback order (proposed): connector → extractor → local key-value

### 4) BOM Import (Assemblies)
- Connector returns BOM graph; Yuantus maps to Item/BOM line (Relationship-as-Item).

## Connector Selection (3D)
- Use existing `cad_connector_id` + `cad_format` resolution in `cad_router.py`.
- 3D plugin registry should match:
  - **cad_format** (NX/CREO/SOLIDWORKS/CATIA/INVENTOR)
  - **document_type = 3d**
  - **file extensions**: prt/asm/sldprt/sldasm/catpart/ipt/etc.

## Multi-Tenant Isolation
- `tenant_id` + `org_id` passed to connector
- Connector must treat artifacts as tenant-scoped
- Prefer signed URLs scoped to tenant/org

## Security
- Optional service token (`CAD_CONNECTOR_SERVICE_TOKEN`)
- Support independent auth header for connector to avoid JWT conflicts
- Use short-lived signed URLs for file_url + artifact urls

## Deployment Patterns
1) **Local Stub** (CI/dev): `services/cad-connector/`
2) **Single Host, Multi-Plugin**: one service with plugin registry
3) **Per-Connector Service**: separate container per vendor (license isolation)

## Verification Plan
- **Stub contract**: `scripts/verify_cad_connector_stub.sh`
- **PLM 3D metadata**: `scripts/verify_cad_connectors_3d.sh`
- **E2E connector** (future): upload real .prt/.sldprt, verify geometry preview URL + BOM import

## Acceptance Criteria
- Connector health + capabilities reachable
- `/convert` returns valid artifacts (geometry + preview + attributes)
- PLM metadata contains correct `cad_format`, `cad_connector_id`, `document_type=3d`
- BOM import succeeds for assemblies (when available)

## Next Implementation Steps
1) Add `CadConnectorClient` and settings (`CAD_CONNECTOR_BASE_URL`, `CAD_CONNECTOR_SERVICE_TOKEN`)
2) Wire connector to `cad_pipeline_tasks.py` for geometry/preview/bom
3) Add async callback handling in API (optional)
4) Onboard first real plugin (Creo or NX) with real file samples
