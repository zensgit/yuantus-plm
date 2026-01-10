# Stage 2 Development Report - Document reopen + Metadata API

Date: 2026-01-09

## Goal
Introduce CAD document schema version tracking and a lightweight metadata API
for CAD-related properties.

## Changes Delivered
- Added `cad_document_schema_version` to `meta_files` and exposed it through
  CAD import and file metadata responses.
- Added `cad_properties` storage with timestamps and source tagging.
- Implemented CAD properties API endpoints:
  - `GET /api/v1/cad/files/{file_id}/properties`
  - `PATCH /api/v1/cad/files/{file_id}/properties`
- Extracted document schema version from CADGF manifest/document during
  `cad_geometry` processing.

## Files Touched
- `src/yuantus/meta_engine/models/file.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `migrations/versions/i1b2c3d4e5f7_add_cad_document_schema_version.py`

## Notes
- Schema version is pulled from CADGF `manifest.json` (fallback to
  `document.json` if needed).
