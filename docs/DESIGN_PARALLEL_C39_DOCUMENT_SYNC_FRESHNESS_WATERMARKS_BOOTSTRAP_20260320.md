# C39 -- Document Sync Freshness / Watermarks Bootstrap -- Design

## Goal
- Extend the isolated `document_sync` domain with freshness, watermark, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Planned API
- `GET /api/v1/document-sync/freshness/overview`
- `GET /api/v1/document-sync/watermarks/summary`
- `GET /api/v1/document-sync/sites/{site_id}/freshness`
- `GET /api/v1/document-sync/export/watermarks`

## Planned Service Methods
- `freshness_overview()` -- Fleet-wide freshness distribution summary
- `watermarks_summary()` -- Watermark coverage and lag summary
- `site_freshness(site_id)` -- Per-site freshness detail
- `export_watermarks()` -- Export-ready freshness/watermark payload

## Constraints
- No `app.py` registration.
- No background workers or storage hot-path integration.
- Stay inside the isolated `document_sync` domain.
