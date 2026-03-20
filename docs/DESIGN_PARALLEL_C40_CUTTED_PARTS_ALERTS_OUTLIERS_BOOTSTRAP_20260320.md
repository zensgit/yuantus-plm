# C40 -- Cutted Parts Alerts / Outliers Bootstrap -- Design

## Goal
- Extend the isolated `cutted_parts` domain with alerts, outliers, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Planned API
- `GET /api/v1/cutted-parts/alerts/overview`
- `GET /api/v1/cutted-parts/outliers/summary`
- `GET /api/v1/cutted-parts/plans/{plan_id}/alerts`
- `GET /api/v1/cutted-parts/export/outliers`

## Planned Service Methods
- `alerts_overview()` -- Fleet-wide alert counts and severity summary
- `outliers_summary()` -- Material and plan outlier summary
- `plan_alerts(plan_id)` -- Per-plan alert detail
- `export_outliers()` -- Export-ready alert/outlier payload

## Constraints
- No `app.py` registration.
- No optimization solver or BOM/manufacturing hot-path integration.
- Stay inside the isolated `cutted_parts` domain.
