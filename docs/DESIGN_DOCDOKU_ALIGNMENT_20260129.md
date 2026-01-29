# DocDoku Alignment – UI/Integration Mapping (2026-01-29)

## Goal
Align Yuantus CAD integration and UI contract with DocDoku-style expectations across preview, metadata, and assembly/BOM structure.

## Reference (DocDoku style)
- Dedicated conversion microservice
- Extension-based converter selection
- Normalized outputs: geometry + preview + metadata + BOM

## Yuantus Mapping
| DocDoku Concept | Yuantus Endpoint | Notes |
| --- | --- | --- |
| File preview | `GET /api/v1/file/{id}/preview` | S3 mode returns 302 to presigned URL |
| Geometry/3D | `GET /api/v1/file/{id}/geometry` | 3D viewer assets (gltf/mesh) |
| CAD manifest | `GET /api/v1/file/{id}/cad_manifest` | viewer manifest + rewrite option |
| CAD document JSON | `GET /api/v1/file/{id}/cad_document` | structured entity payload |
| CAD metadata JSON | `GET /api/v1/file/{id}/cad_metadata` | extracted attributes |
| CAD BOM | `GET /api/v1/cad/files/{file_id}/bom` | assembly/bom extraction |
| Connector list | `GET /api/v1/cad/connectors` | capability matrix |
| Convert/import | `POST /api/v1/cad/import` | job enqueue for preview/geometry/extract/bom |

## Coverage Notes
- DocDoku-style converter contract already documented in `DESIGN_CAD_CONNECTOR_PLUGIN_SPEC_20260127.md`.
- Built-in connectors map to 2D/3D formats; external connectors integrate via config/reload.
- Viewer flow uses `cad_manifest_url` and `cad_viewer_url` for UI launch.

## Gaps / Next Iteration
- Expose a consolidated **"cad capabilities"** endpoint (formats + features) for UI autodiscovery.
- Add optional `cad_bom` schema validation (nodes/edges contract).

## Verification
- `docs/VERIFICATION_CAD_CONNECTOR_MATRIX_20260129_2116.md`
- Plugin framework verification (capabilities + config exposure)
- DocDoku alignment script requires an existing admin user (run `seed-identity` if needed).
- When CAD ML is unavailable, set `CAD_PREVIEW_ALLOW_FALLBACK=1` to continue with fallback preview.
