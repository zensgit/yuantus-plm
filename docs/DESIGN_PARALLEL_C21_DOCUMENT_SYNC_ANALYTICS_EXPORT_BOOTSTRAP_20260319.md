# C21 – Document Sync Analytics / Export Bootstrap – Design

## Goal
- 在独立 `document_sync` 子域内补第二阶段 analytics / conflict / export 能力。
- 保持 `C18` 的 greenfield 隔离，不接入 `app.py`。

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Deliverables
- site/job overview analytics
- conflict summary read model
- export-ready sync summary payload
- router-level analytics/export endpoints

## Suggested API
- `GET /api/v1/document-sync/overview`
- `GET /api/v1/document-sync/sites/{site_id}/analytics`
- `GET /api/v1/document-sync/jobs/{job_id}/conflicts`
- `GET /api/v1/document-sync/export/overview`
- `GET /api/v1/document-sync/export/conflicts`

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 storage/CAD hot path
- 不加 background workers
