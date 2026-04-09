# C42 Design: Document Sync Lag / Backlog Bootstrap

## Overview
Extends the document sync domain with lag visibility, backlog summaries,
and export helpers for downstream reporting.

## Planned Service Methods

### lag_overview()
Cross-site lag summary: total jobs, delayed jobs, avg lag proxy,
and lag distribution by status.

### backlog_summary()
Backlog summary: queued vs completed ratios, backlog depth stats,
and per-site pending distribution.

### site_backlog(site_id)
Per-site lag and backlog detail: site info, job counts,
status distribution, and delayed job indicators. Raises ValueError if site not found.

### export_backlog()
Export-ready payload combining lag_overview, backlog_summary,
and per-site backlog detail.

## Planned Router Endpoints

| Method | Path                       | Service Method     |
|--------|----------------------------|--------------------|
| GET    | /lag/overview              | lag_overview()     |
| GET    | /backlog/summary           | backlog_summary()  |
| GET    | /sites/{site_id}/backlog   | site_backlog()     |
| GET    | /export/backlog            | export_backlog()   |

## Patterns
- Follows established `C39` / `C36` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
