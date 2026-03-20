# C38 Design: PLM Box Allocation / Custody Bootstrap

## Overview
Extends the PLM box domain with allocation tracking, custody chain analysis,
and export helpers for downstream integration.

## Service Methods

### allocations_overview()
Fleet-wide allocation summary: total boxes, allocated vs unallocated,
allocation rate, boxes by state.

### custody_summary()
Custody chain summary: boxes with contents, custody depth stats,
avg contents per box.

### box_custody(box_id)
Per-box custody detail: box info, contents list, custody depth,
total quantity. Raises ValueError if box not found.

### export_custody()
Export-ready payload combining allocations_overview, custody_summary,
and per-box custody details.

## Router Endpoints

| Method | Path                          | Service Method            |
|--------|-------------------------------|---------------------------|
| GET    | /allocations/overview         | allocations_overview()    |
| GET    | /custody/summary              | custody_summary()         |
| GET    | /items/{box_id}/custody       | box_custody(box_id)       |
| GET    | /export/custody               | export_custody()          |

## Patterns
- Follows established C32/C35 section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
