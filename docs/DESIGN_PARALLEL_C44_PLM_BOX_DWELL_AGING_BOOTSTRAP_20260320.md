# C44 Design: PLM Box Dwell / Aging Bootstrap

## Overview
Extends the PLM box domain with dwell-time visibility, aging summaries,
and export helpers for downstream reporting.

## Service Methods

### dwell_overview()
Fleet-wide dwell summary: total boxes, avg items per box,
boxes with high item count (>10), boxes with low item count (<=2).

### aging_summary()
Aging summary: boxes grouped by age tier based on item count.
- mature: >10 items (heavily used)
- active: 4-10 items
- fresh: 0-3 items (newly created or underutilized)

### box_aging(box_id)
Per-box aging detail: box info, item count, age tier,
item breakdown with contents list. Raises ValueError if box not found.

### export_aging()
Export-ready payload combining dwell_overview, aging_summary,
and per-box aging detail for all boxes.

## Router Endpoints

| Method | Path                  | Service Method   |
|--------|-----------------------|------------------|
| GET    | /dwell/overview       | dwell_overview() |
| GET    | /aging/summary        | aging_summary()  |
| GET    | /items/{box_id}/aging | box_aging()      |
| GET    | /export/aging         | export_aging()   |

## Age Tier Classification

| Tier   | Item Count | Description                    |
|--------|------------|--------------------------------|
| mature | >10        | Heavily used                   |
| active | 4-10       | Normal usage                   |
| fresh  | 0-3        | Newly created or underutilized |

## Patterns
- Follows established C41 / C38 section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
