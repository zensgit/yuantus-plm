# C33 -- Document Sync Baseline / Lineage Bootstrap -- Design

## Goal
- Extend the isolated `document_sync` domain with baseline, lineage, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Implemented API
- `GET /api/v1/document-sync/baseline/overview`
- `GET /api/v1/document-sync/sites/{site_id}/lineage`
- `GET /api/v1/document-sync/jobs/{job_id}/snapshot-lineage`
- `GET /api/v1/document-sync/export/lineage`

## Service Methods
- `baseline_overview()` -- fleet-wide baseline metrics (coverage pct, sites with baseline)
- `site_lineage(site_id)` -- per-site lineage (job history, sync aggregates, lineage depth)
- `job_snapshot_lineage(job_id)` -- per-job snapshot (completeness, is_baseline flag, records by outcome)
- `export_lineage()` -- export-ready combined payload

## Tests
### Service (10 tests in TestBaselineLineage)
- test_baseline_overview
- test_baseline_overview_empty
- test_site_lineage
- test_site_lineage_no_jobs
- test_site_lineage_not_found
- test_job_snapshot_lineage
- test_job_snapshot_lineage_pending
- test_job_snapshot_lineage_not_found
- test_export_lineage
- test_export_lineage_empty

### Router (6 tests)
- test_baseline_overview
- test_site_lineage
- test_site_lineage_not_found_404
- test_job_snapshot_lineage
- test_job_snapshot_lineage_not_found_404
- test_export_lineage

## Constraints
- No `app.py` registration.
- No background workers.
- Stay inside the isolated `document_sync` domain.
