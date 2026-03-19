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

## New Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `overview()` | Dict | Site/job totals, state/direction breakdowns, conflict/error totals |
| `site_analytics(site_id)` | Dict | Per-site job counts, synced/conflict/error/skipped aggregates |
| `job_conflicts(job_id)` | Dict | Conflict-only records for a specific job |
| `export_overview()` | Dict | Export-ready combined overview payload |
| `export_conflicts()` | Dict | Cross-job conflict summary for export |

## New API Endpoints

| Method | Path | Handler |
|--------|------|---------|
| GET | `/overview` | High-level site/job overview |
| GET | `/sites/{site_id}/analytics` | Per-site analytics |
| GET | `/jobs/{job_id}/conflicts` | Per-job conflict list |
| GET | `/export/overview` | Export-ready overview |
| GET | `/export/conflicts` | Export-ready conflict summary |

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 storage/CAD hot path
- 不加 background workers
