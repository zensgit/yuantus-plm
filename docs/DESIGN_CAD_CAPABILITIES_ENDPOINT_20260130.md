# CAD Capabilities Endpoint Design (2026-01-30)

## Goal
Expose a single endpoint that summarizes CAD connector formats, extensions, feature support, and integration configuration for UI autodiscovery.

## Endpoint
`GET /api/v1/cad/capabilities`

## Response (Shape)
- `connectors`: list of connector info (same as `/cad/connectors`)
- `counts`: total/2d/3d
- `formats`: grouped by document_type
- `extensions`: grouped by document_type
- `features`: preview/geometry/extract/bom/manifest/metadata with available modes
- `integrations`: configured service base URLs + modes

## Notes
- This endpoint reflects configuration (no health checks).
- BOM capability is marked available only when CAD connector service is configured.
