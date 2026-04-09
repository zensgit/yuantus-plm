# Design: C41 PLM Box Occupancy / Turnover Bootstrap

## Overview
Extends the PLM box domain with occupancy, turnover, and export helpers.

## Service Methods
- `occupancy_overview()` — Fleet-wide occupancy summary: total boxes, occupied vs empty, occupancy rate, avg fill level.
- `turnover_summary()` — Turnover summary across the fleet: active boxes, avg contents, high/low turnover detection.
- `box_turnover(box_id)` — Per-box turnover detail: contents count, fill ratio, turnover classification.
- `export_turnover()` — Export-ready payload combining occupancy_overview, turnover_summary, and per-box turnover.

## Router Endpoints
- `GET /occupancy/overview`
- `GET /turnover/summary`
- `GET /items/{box_id}/turnover` (404 on missing box)
- `GET /export/turnover`

## Classification Logic
- **high**: contents_count >= 5
- **low**: contents_count == 0
- **normal**: otherwise
