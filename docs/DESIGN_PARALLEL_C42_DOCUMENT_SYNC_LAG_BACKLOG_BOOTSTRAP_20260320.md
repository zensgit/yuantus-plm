# C42 Design: Document Sync Lag / Backlog Bootstrap

## Overview
Extends the document sync domain with lag visibility, backlog summaries,
and export helpers for downstream reporting.

## Service Methods

### lag_overview()
Fleet-wide sync lag summary: total sites, sites with pending/failed
jobs, avg lag score (pending+failed per site), worst-lag site.

### backlog_summary()
Backlog summary: total pending jobs across fleet, sites with
backlog above threshold (>3 pending jobs), backlog distribution per site.

### site_backlog(site_id)
Per-site backlog detail: site info, pending/failed/synced job counts,
backlog depth (pending + failed). Raises ValueError if site not found.

### export_backlog()
Export-ready payload combining lag_overview, backlog_summary,
and per-site backlog detail for all sites.

## Router Endpoints

| Method | Path                       | Service Method     | Error Handling |
|--------|----------------------------|--------------------|----------------|
| GET    | /lag/overview              | lag_overview()     | -              |
| GET    | /backlog/summary           | backlog_summary()  | -              |
| GET    | /sites/{site_id}/backlog   | site_backlog()     | ValueError->404|
| GET    | /export/backlog            | export_backlog()   | -              |

## Key Decisions
- Lag metric = count of pending + failed jobs per site (simple, queryable)
- Backlog threshold = 3 (sites with >3 pending jobs flagged)
- Follows established C33/C36/C39 section patterns
- No new models or migrations required
