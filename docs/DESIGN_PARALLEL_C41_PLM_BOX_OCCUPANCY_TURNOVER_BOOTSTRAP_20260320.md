# C41 Design: PLM Box Occupancy / Turnover Bootstrap

## Overview
Extends the PLM box domain with occupancy tracking, turnover summaries,
and export helpers for downstream integration.

## Planned Service Methods

### occupancy_overview()
Fleet-wide occupancy summary: total boxes, occupied vs empty, occupancy rate,
boxes by state.

### turnover_summary()
Turnover summary: contents movement density, avg refill count proxy,
and box reuse distribution.

### box_turnover(box_id)
Per-box occupancy and turnover detail: box info, content count,
quantity totals, and reuse markers. Raises ValueError if box not found.

### export_turnover()
Export-ready payload combining occupancy_overview, turnover_summary,
and per-box turnover detail.

## Planned Router Endpoints

| Method | Path                    | Service Method       |
|--------|-------------------------|----------------------|
| GET    | /occupancy/overview     | occupancy_overview() |
| GET    | /turnover/summary       | turnover_summary()   |
| GET    | /items/{box_id}/turnover| box_turnover(box_id) |
| GET    | /export/turnover        | export_turnover()    |

## Patterns
- Follows established `C38` / `C35` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
