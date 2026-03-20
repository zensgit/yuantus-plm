# C43 Design: Cutted Parts Throughput / Cadence Bootstrap

## Overview
Extends the cutted_parts domain with throughput tracking, cadence summaries,
and export helpers for downstream planning.

## Planned Service Methods

### throughput_overview()
Plan-wide throughput summary: total plans, total cuts, avg cuts per plan,
and throughput distribution.

### cadence_summary()
Cadence summary: plan density, material usage rhythm,
and output consistency indicators.

### plan_cadence(plan_id)
Per-plan throughput and cadence detail: plan info, cut totals,
yield context, and cadence indicators. Raises ValueError if plan not found.

### export_cadence()
Export-ready payload combining throughput_overview, cadence_summary,
and per-plan cadence detail.

## Planned Router Endpoints

| Method | Path                         | Service Method        |
|--------|------------------------------|-----------------------|
| GET    | /throughput/overview         | throughput_overview() |
| GET    | /cadence/summary             | cadence_summary()     |
| GET    | /plans/{plan_id}/cadence     | plan_cadence(plan_id) |
| GET    | /export/cadence              | export_cadence()      |

## Patterns
- Follows established `C40` / `C37` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
