# C43 -- Cutted Parts Throughput / Cadence Bootstrap -- Design

## Goal
- Extend the isolated `cutted_parts` domain with throughput tracking, cadence tiering, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `throughput_overview()` | Dict | Fleet-wide throughput: total cuts, avg cuts/plan, max/min plan, fleet yield |
| `cadence_summary()` | Dict | Plans grouped by cadence tier: high (>=5), medium (2-4), low (0-1) |
| `plan_cadence(plan_id)` | Dict | Per-plan cadence: cut breakdown, yield, tier classification |
| `export_cadence()` | Dict | Export-ready throughput + cadence + per-plan cadences |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/throughput/overview` | `service.throughput_overview()` | -- |
| GET | `/cadence/summary` | `service.cadence_summary()` | -- |
| GET | `/plans/{plan_id}/cadence` | `service.plan_cadence(plan_id)` | ValueError -> 404 |
| GET | `/export/cadence` | `service.export_cadence()` | -- |

## Tests Added

### Service (15 tests in TestThroughputCadence)
- test_throughput_overview, test_throughput_overview_empty, test_throughput_overview_no_cuts
- test_cadence_summary_high, test_cadence_summary_medium, test_cadence_summary_empty, test_cadence_summary_low
- test_plan_cadence, test_plan_cadence_high_tier, test_plan_cadence_low_tier, test_plan_cadence_no_cuts, test_plan_cadence_not_found
- test_export_cadence, test_export_cadence_empty

### Router (5 tests)
- test_throughput_overview, test_cadence_summary, test_plan_cadence, test_plan_cadence_not_found_404
- test_export_cadence

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
