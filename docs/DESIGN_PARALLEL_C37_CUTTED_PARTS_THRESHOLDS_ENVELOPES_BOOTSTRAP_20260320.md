# C37 -- Cutted Parts Thresholds / Envelopes Bootstrap -- Design

## Goal
- Extend the isolated `cutted_parts` domain with threshold checking, envelope analysis, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `thresholds_overview()` | Dict | Fleet-wide threshold hit-rate: waste >10%, scrap >30%, yield <50% breach counts |
| `envelopes_summary()` | Dict | Per-material waste envelope (min/max) vs 15% limit |
| `plan_threshold_check(plan_id)` | Dict | Per-plan pass/fail on waste, scrap, yield thresholds |
| `export_envelopes()` | Dict | Export-ready thresholds + envelopes + per-plan checks |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/thresholds/overview` | `service.thresholds_overview()` | -- |
| GET | `/envelopes/summary` | `service.envelopes_summary()` | -- |
| GET | `/plans/{plan_id}/threshold-check` | `service.plan_threshold_check(plan_id)` | ValueError -> 404 |
| GET | `/export/envelopes` | `service.export_envelopes()` | -- |

## Tests Added

### Service (16 tests in TestThresholdsEnvelopes)
- test_thresholds_overview, test_thresholds_overview_empty, test_thresholds_overview_scrap_breach, test_thresholds_overview_yield_breach
- test_envelopes_summary, test_envelopes_summary_exceeded, test_envelopes_summary_empty, test_envelopes_summary_no_plans
- test_plan_threshold_check_all_pass, test_plan_threshold_check_waste_fail, test_plan_threshold_check_scrap_fail, test_plan_threshold_check_yield_fail, test_plan_threshold_check_not_found, test_plan_threshold_check_no_cuts
- test_export_envelopes, test_export_envelopes_empty

### Router (6 tests)
- test_thresholds_overview, test_envelopes_summary, test_plan_threshold_check, test_plan_threshold_check_not_found_404
- test_export_envelopes

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
