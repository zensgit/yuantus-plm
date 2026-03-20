# C46 Design: Cutted Parts Saturation / Bottlenecks Bootstrap

## Overview
Extends the cutted_parts domain with saturation visibility, bottleneck summaries,
and export helpers for downstream planning.

## Planned Service Methods

### saturation_overview()
Plan-wide saturation summary: heavily loaded plans, cut density,
and saturation buckets.

### bottlenecks_summary()
Bottleneck summary: constrained materials, plan congestion indicators,
and throughput blockers.

### plan_bottlenecks(plan_id)
Per-plan saturation and bottleneck detail: plan info, cut totals,
material stress markers, and yield context. Raises ValueError if plan not found.

### export_bottlenecks()
Export-ready payload combining saturation_overview, bottlenecks_summary,
and per-plan bottleneck detail.

## Planned Router Endpoints

| Method | Path                            | Service Method        |
|--------|---------------------------------|-----------------------|
| GET    | /saturation/overview            | saturation_overview() |
| GET    | /bottlenecks/summary            | bottlenecks_summary() |
| GET    | /plans/{plan_id}/bottlenecks    | plan_bottlenecks()    |
| GET    | /export/bottlenecks             | export_bottlenecks()  |

## Patterns
- Follows established `C43` / `C40` section patterns
- ValueError -> HTTPException(404)
- No new models or migrations required
