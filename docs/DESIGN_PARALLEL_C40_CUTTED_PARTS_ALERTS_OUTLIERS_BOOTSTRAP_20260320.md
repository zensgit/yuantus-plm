# C40 -- Cutted Parts Alerts / Outliers Bootstrap -- Design

## Goal
- Extend the isolated `cutted_parts` domain with alerts, outlier detection, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `alerts_overview()` | Dict | Fleet-wide alert summary: critical (waste >15%, scrap >30%), warning (waste >10%, yield <50%) |
| `outliers_summary()` | Dict | Statistical outlier detection: plans with waste > mean + 2*std |
| `plan_alerts(plan_id)` | Dict | Per-plan alert detail with level, metric, value, threshold, message |
| `export_outliers()` | Dict | Export-ready alerts + outliers + per-plan alerts |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/alerts/overview` | `service.alerts_overview()` | -- |
| GET | `/outliers/summary` | `service.outliers_summary()` | -- |
| GET | `/plans/{plan_id}/alerts` | `service.plan_alerts(plan_id)` | ValueError -> 404 |
| GET | `/export/outliers` | `service.export_outliers()` | -- |

## Tests Added

### Service (16 tests in TestAlertsOutliers)
- test_alerts_overview, test_alerts_overview_empty, test_alerts_overview_scrap_critical, test_alerts_overview_yield_warning
- test_outliers_summary, test_outliers_summary_with_outlier, test_outliers_summary_empty, test_outliers_summary_single_plan
- test_plan_alerts_clean, test_plan_alerts_critical_waste, test_plan_alerts_warning_waste, test_plan_alerts_scrap_and_yield, test_plan_alerts_not_found, test_plan_alerts_no_cuts
- test_export_outliers, test_export_outliers_empty

### Router (5 tests)
- test_alerts_overview, test_outliers_summary, test_plan_alerts, test_plan_alerts_not_found_404
- test_export_outliers

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
