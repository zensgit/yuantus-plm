# C45 Design: Document Sync Skew / Gaps Bootstrap

## Overview
Extends the document sync domain with skew visibility, gap summaries,
and export helpers for downstream reporting.

## Service Methods (Implemented)

### skew_overview()
Fleet-wide skew summary: total sites, sites with sync gaps (pending/failed
jobs), avg gap count across sites, worst-gap site (most gaps).

### gaps_summary()
Gaps summary: total gaps across fleet, sites with gaps above threshold (>2),
gap distribution by severity (critical >5, warning 3-5, minor 1-2, clean 0).

### site_gaps(site_id)
Per-site gap detail: site info, pending/failed job counts, gap count,
severity level. Raises ValueError if site not found.

### export_gaps()
Export-ready payload combining skew_overview, gaps_summary,
and per-site gap details for all sites.

## Router Endpoints (Implemented)

| Method | Path                  | Service Method  | Error Handling       |
|--------|-----------------------|-----------------|----------------------|
| GET    | /skew/overview        | skew_overview() | -                    |
| GET    | /gaps/summary         | gaps_summary()  | -                    |
| GET    | /sites/{site_id}/gaps | site_gaps()     | ValueError -> 404    |
| GET    | /export/gaps          | export_gaps()   | -                    |

## Patterns
- Follows established `C42` / `C39` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
- Gap = job with state "pending" or "failed"
- Severity thresholds: critical(>5), warning(3-5), minor(1-2), clean(0)
- Gap threshold for flagging sites: >2 gap jobs
