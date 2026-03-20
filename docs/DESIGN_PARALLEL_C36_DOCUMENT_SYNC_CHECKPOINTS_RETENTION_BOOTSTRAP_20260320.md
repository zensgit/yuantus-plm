# C36 -- Document Sync Checkpoints / Retention Bootstrap -- Design

## Goal
- Extend the isolated `document_sync` domain with checkpoint, retention, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Planned API
- `GET /api/v1/document-sync/checkpoints/overview`
- `GET /api/v1/document-sync/retention/summary`
- `GET /api/v1/document-sync/sites/{site_id}/checkpoints`
- `GET /api/v1/document-sync/export/retention`

## Planned Service Methods
- `checkpoints_overview()` -- Fleet-wide checkpoint coverage summary
- `retention_summary()` -- Snapshot retention age / expiry summary
- `site_checkpoints(site_id)` -- Per-site checkpoint detail and recent sequence
- `export_retention()` -- Export-ready checkpoint/retention payload

## Constraints
- No `app.py` registration.
- No background workers or storage hot-path integration.
- Stay inside the isolated `document_sync` domain.
