# C30 -- Document Sync Drift / Snapshots Bootstrap -- Design

## Goal
- Extend the `document_sync` sub-domain with drift detection, snapshot mismatch, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_service.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `drift_overview()` | Dict | Fleet-wide drift metrics: jobs with issues, drift rate, failed-site count, synced document totals |
| `site_snapshots(site_id)` | Dict | Per-site snapshot health: completed jobs ratio, sync totals, latest job state |
| `job_drift(job_id)` | Dict | Per-job drift detail: completeness percentage, drift detection flag, records breakdown |
| `export_drift()` | Dict | Export-ready drift payload combining overview + per-site snapshots |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/drift/overview` | `service.drift_overview()` | -- |
| GET | `/sites/{site_id}/snapshots` | `service.site_snapshots(site_id)` | ValueError -> 404 |
| GET | `/jobs/{job_id}/drift` | `service.job_drift(job_id)` | ValueError -> 404 |
| GET | `/export/drift` | `service.export_drift()` | -- |

## Tests

### Service Tests (TestDriftSnapshots) -- 10 tests
- test_drift_overview
- test_drift_overview_empty
- test_site_snapshots
- test_site_snapshots_no_jobs
- test_site_snapshots_not_found
- test_job_drift
- test_job_drift_clean
- test_job_drift_not_found
- test_export_drift
- test_export_drift_empty

### Router Tests -- 6 tests
- test_drift_overview
- test_site_snapshots
- test_site_snapshots_not_found_404
- test_job_drift
- test_job_drift_not_found_404
- test_export_drift

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No background workers or storage hot-path integration
