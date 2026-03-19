# C24 - Document Sync Reconciliation Bootstrap - Design

## Goal
Extend the isolated `document_sync` domain with reconciliation and conflict-resolution read helpers while keeping the module greenfield and self-contained.

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## API Surface

### Service Methods (C24 additions)

| Method | Input | Output | Errors |
|--------|-------|--------|--------|
| `reconciliation_queue()` | none | `{total_jobs_with_conflicts, jobs[]}` | -- |
| `conflict_resolution_summary(job_id)` | job_id: str | `{job_id, site_id, state, total_records, synced, conflicts, errors, skipped, conflict_details[], error_details[]}` | ValueError if job not found |
| `site_reconciliation_status(site_id)` | site_id: str | `{site_id, site_name, state, total_jobs, jobs_with_conflicts, jobs_with_errors, total_unresolved_conflicts, total_unresolved_errors}` | ValueError if site not found |
| `export_reconciliation()` | none | `{reconciliation_queue, sites[]}` | -- |

### Router Endpoints (C24 additions)

| Method | Path | Service Call | Error Mapping |
|--------|------|-------------|---------------|
| GET | `/document-sync/reconciliation/queue` | `reconciliation_queue()` | -- |
| GET | `/document-sync/reconciliation/jobs/{job_id}/summary` | `conflict_resolution_summary(job_id)` | ValueError -> 404 |
| GET | `/document-sync/reconciliation/sites/{site_id}/status` | `site_reconciliation_status(site_id)` | ValueError -> 404 |
| GET | `/document-sync/export/reconciliation` | `export_reconciliation()` | -- |

## Implementation Details

### Reconciliation Queue Logic
- Filters jobs by state in `{completed, failed}` AND `conflict_count > 0`
- Pending/running/cancelled jobs are excluded (not yet actionable)
- Returns list of job summaries with conflict and error counts

### Conflict Resolution Summary
- Iterates all records for a job, categorizing by outcome
- Returns record-level detail for conflicts (record_id, document_id, checksums, detail)
- Returns record-level detail for errors (record_id, document_id, detail)
- Counts synced, conflicts, errors, skipped separately

### Site Reconciliation Status
- Aggregates across all jobs for a given site
- Counts jobs with any conflicts and jobs with any errors
- Sums total unresolved conflicts and errors across all jobs

### Export Reconciliation
- Combines reconciliation_queue with per-site breakdown
- Queries all SyncSite objects and maps through site_reconciliation_status

## Non-Goals
- no app registration
- no background workers
- no storage/CAD hot-path integration
- no write/mutation operations for conflict resolution
