# CAD Connector Stub (Design)

## Goal
Provide a DocDoku-style conversion microservice stub that implements the connector
contract and returns normalized artifacts for integration testing.

## Endpoints
- `GET /health`
- `GET /api/v1/health`
- `GET /capabilities`
- `POST /convert` / `POST /api/v1/convert`
- `GET /jobs/{job_id}` (async mode)
- `GET /artifacts/{id}/mesh.gltf`
- `GET /artifacts/{id}/mesh.bin`
- `GET /artifacts/{id}/preview.png`

## Behavior
- Parses filename to derive `part_number`, `description`, `revision`.
- Returns stub geometry/preview URLs and empty BOM structure.
- Optional async mode returns `job_id` with completed status.

## Usage
- Service location: `services/cad-connector/`
- Verification script: `scripts/verify_cad_connector_stub.sh`
- Report: `docs/VERIFICATION_CAD_CONNECTOR_STUB_20260127.md`

## Relationship to Spec
This stub implements the contract defined in
`docs/DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`.
