# C11 – File/3D Viewer Consumer Hardening

**Branch**: `feature/claude-c11-file-viewer-consumer`
**Date**: 2026-03-19
**Status**: Implemented & Verified

---

## 1. Objective

Extend the C3 viewer readiness surface with consumer-facing read
endpoints: one-stop summary, batch readiness export, and geometry
asset pack aggregation.

## 2. New Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/file/{file_id}/consumer-summary` | One-stop viewer client summary |
| POST | `/file/viewer-readiness/export` | Batch readiness export (JSON/CSV) |
| POST | `/file/geometry-pack-summary` | Aggregate geometry asset info |

### GET /file/{file_id}/consumer-summary

Returns everything a viewer client needs in a single call:
- viewer_mode, is_viewer_ready, geometry_format
- available assets list
- blocking_reasons
- pre-built URLs for geometry, preview, manifest, download

### POST /file/viewer-readiness/export

Accepts `{"file_ids": [...]}` and returns readiness status for each file.
Supports `export_format=json` (default) or `export_format=csv`.
Missing files are included with `viewer_mode: "not_found"`.

### POST /file/geometry-pack-summary

Accepts `{"file_ids": [...]}` and returns:
- total_files, files_found, viewer_ready_count
- total_assets across all files
- format_counts (e.g., `{"glb": 3, "obj": 1}`)
- per-file pack details

## 3. Design Decisions

1. **POST for batch endpoints**: Batch operations use POST to allow
   large file_ids lists without URL length constraints.

2. **Graceful missing files**: All batch endpoints include missing
   files in the response with `found: false` rather than failing.

3. **No new service methods**: All three endpoints compose existing
   `assess_viewer_readiness()` from C3 — no new service layer needed.

4. **CSV export streaming**: CSV export uses `StreamingResponse` for
   consistent download behavior with Content-Disposition headers.
