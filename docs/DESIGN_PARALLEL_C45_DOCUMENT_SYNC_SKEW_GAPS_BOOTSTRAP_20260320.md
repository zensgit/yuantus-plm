# C45 Design: Document Sync Skew / Gaps Bootstrap

## Overview
Extends the document sync domain with skew visibility, gap summaries,
and export helpers for downstream reporting.

## Planned Service Methods

### skew_overview()
Cross-site skew summary: job skew buckets, delayed distributions,
and skew severity proxies.

### gaps_summary()
Gap summary: missing sync windows, incomplete coverage ratios,
and per-site gap density.

### site_gaps(site_id)
Per-site skew and gap detail: site info, skew markers,
gap windows, and status counts. Raises ValueError if site not found.

### export_gaps()
Export-ready payload combining skew_overview, gaps_summary,
and per-site gap detail.

## Planned Router Endpoints

| Method | Path                  | Service Method  |
|--------|-----------------------|-----------------|
| GET    | /skew/overview        | skew_overview() |
| GET    | /gaps/summary         | gaps_summary()  |
| GET    | /sites/{site_id}/gaps | site_gaps()     |
| GET    | /export/gaps          | export_gaps()   |

## Patterns
- Follows established `C42` / `C39` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
