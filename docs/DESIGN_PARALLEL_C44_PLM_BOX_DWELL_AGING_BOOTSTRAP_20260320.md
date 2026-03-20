# C44 Design: PLM Box Dwell / Aging Bootstrap

## Overview
Extends the PLM box domain with dwell-time visibility, aging summaries,
and export helpers for downstream reporting.

## Planned Service Methods

### dwell_overview()
Fleet-wide dwell summary: total boxes, active vs stale, dwell buckets,
and dwell trend proxies.

### aging_summary()
Aging summary: stale inventory ratio, aging tiers,
and box state distribution.

### box_aging(box_id)
Per-box dwell and aging detail: box info, content age proxy,
state, and occupancy context. Raises ValueError if box not found.

### export_aging()
Export-ready payload combining dwell_overview, aging_summary,
and per-box aging detail.

## Planned Router Endpoints

| Method | Path                 | Service Method   |
|--------|----------------------|------------------|
| GET    | /dwell/overview      | dwell_overview() |
| GET    | /aging/summary       | aging_summary()  |
| GET    | /items/{box_id}/aging| box_aging()      |
| GET    | /export/aging        | export_aging()   |

## Patterns
- Follows established `C41` / `C38` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
