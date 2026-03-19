# C30 -- Document Sync Drift / Snapshots Bootstrap -- Design

## Goal
- Extend the `document_sync` sub-domain with drift detection, snapshot mismatch, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_service.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`

## Suggested Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `drift_overview()` | Dict | Site/job drift counts, mismatch breakdowns, stale snapshot counts |
| `site_snapshots(site_id)` | Dict | Per-site snapshot health and mismatch detail |
| `job_drift(job_id)` | Dict | Per-job drift and reconciliation eligibility detail |
| `export_drift()` | Dict | Export-ready drift payload |

## Suggested API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/drift/overview` | `service.drift_overview()` | -- |
| GET | `/sites/{site_id}/snapshots` | `service.site_snapshots(site_id)` | ValueError -> 404 |
| GET | `/jobs/{job_id}/drift` | `service.job_drift(job_id)` | ValueError -> 404 |
| GET | `/export/drift` | `service.export_drift()` | -- |

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No background workers or storage hot-path integration
