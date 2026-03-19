# C27 -- Document Sync Replay / Audit Bootstrap -- Design

## Goal
- Extend the `document_sync` sub-domain with replay planning, audit summaries, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_service.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `replay_overview()` | Dict | Fleet-wide: retryable (failed) + replay candidates (completed with issues) |
| `site_audit(site_id)` | Dict | Per-site: completed/failed/cancelled counts, health_pct, outcome totals |
| `job_audit(job_id)` | Dict | Per-job: outcome breakdown, checksum mismatches, is_retryable, has_issues |
| `export_audit()` | Dict | Export-ready: replay_overview + per-site audit breakdown |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/replay/overview` | `service.replay_overview()` | -- |
| GET | `/sites/{site_id}/audit` | `service.site_audit(site_id)` | ValueError -> 404 |
| GET | `/jobs/{job_id}/audit` | `service.job_audit(job_id)` | ValueError -> 404 |
| GET | `/export/audit` | `service.export_audit()` | -- |

## Tests
- Service: 10 tests in `TestReplayAudit` class
- Router: 6 tests for all C27 endpoints

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No background workers or storage hot-path integration
