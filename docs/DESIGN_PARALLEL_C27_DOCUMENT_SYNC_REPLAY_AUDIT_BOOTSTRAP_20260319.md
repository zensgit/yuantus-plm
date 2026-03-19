# C27 -- Document Sync Replay / Audit Bootstrap -- Design

## Goal
- Extend the `document_sync` sub-domain with replay planning, audit summaries, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/document_sync/service.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_service.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`

## Suggested Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `replay_overview()` | Dict | Replay-eligible jobs, failed job counts, direction breakdown |
| `site_audit(site_id)` | Dict | Per-site replay backlog, conflict counts, last sync health |
| `job_audit(job_id)` | Dict | Per-job replay/audit detail and retry eligibility |
| `export_audit()` | Dict | Export-ready combined replay and audit payload |

## Suggested API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/replay/overview` | `service.replay_overview()` | -- |
| GET | `/sites/{site_id}/audit` | `service.site_audit(site_id)` | ValueError -> 404 |
| GET | `/jobs/{job_id}/audit` | `service.job_audit(job_id)` | ValueError -> 404 |
| GET | `/export/audit` | `service.export_audit()` | -- |

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No background workers or storage hot-path integration
