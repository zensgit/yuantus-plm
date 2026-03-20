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
- `checkpoints_overview()` -- Fleet-wide checkpoint coverage: site counts by state, job completion rate, retention readiness flag
- `retention_summary()` -- Record-level retention metrics: synced/conflict/error/skipped counts with percentage breakdowns
- `site_checkpoints(site_id)` -- Per-site checkpoint detail: job list as checkpoints, completion rate, aggregated record metrics
- `export_retention()` -- Export-ready combined payload: checkpoints_overview + retention_summary + per-site checkpoint details

## Data Model
No new models or schema changes. C36 operates on existing `SyncSite`, `SyncJob`, and `SyncRecord` models, computing checkpoint and retention metrics from job-level counters (`synced_count`, `conflict_count`, `error_count`, `skipped_count`).

## Key Design Decisions
- **Retention readiness** (`retention_ready`): True only when `total_errors == 0` and `completed_jobs > 0`, indicating the fleet has at least one successful sync checkpoint with zero errors.
- **Checkpoint granularity**: Each `SyncJob` serves as a checkpoint. Per-site checkpoint lists enumerate all jobs with their individual sync/error/conflict counts.
- **Percentage metrics**: `completion_rate`, `conflict_retention_pct`, `error_retention_pct`, `clean_sync_pct` are computed from aggregate counters. All return `None` when the divisor is zero.

## Constraints
- No `app.py` registration.
- No background workers or storage hot-path integration.
- Stay inside the isolated `document_sync` domain.
