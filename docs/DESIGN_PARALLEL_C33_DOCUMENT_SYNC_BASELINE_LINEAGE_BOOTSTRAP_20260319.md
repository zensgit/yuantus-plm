# C33 -- Document Sync Baseline / Lineage Bootstrap -- Design

## Goal
- Extend the isolated `document_sync` domain with baseline, lineage, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Suggested API
- `GET /api/v1/document-sync/baseline/overview`
- `GET /api/v1/document-sync/sites/{site_id}/lineage`
- `GET /api/v1/document-sync/jobs/{job_id}/snapshot-lineage`
- `GET /api/v1/document-sync/export/lineage`

## Constraints
- No `app.py` registration.
- No background workers.
- Stay inside the isolated `document_sync` domain.
