# C34 -- Cutted Parts Variance / Recommendations Bootstrap -- Design

## Goal
- Extend the `cutted_parts` sub-domain with variance analysis, recommendation engine, and export helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/cutted_parts/service.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `variance_overview()` | Dict | Fleet-wide waste/cost variance: mean, std, range, outlier detection |
| `plan_recommendations(plan_id)` | Dict | Per-plan recommendations with severity based on waste/scrap/yield vs fleet |
| `material_variance()` | Dict | Variance by material: waste mean/std, cost, plan count |
| `export_recommendations()` | Dict | Export-ready variance + material variance + per-plan recommendations |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/variance/overview` | `service.variance_overview()` | -- |
| GET | `/plans/{plan_id}/recommendations` | `service.plan_recommendations(plan_id)` | ValueError -> 404 |
| GET | `/materials/variance` | `service.material_variance()` | -- |
| GET | `/export/recommendations` | `service.export_recommendations()` | -- |

## Tests Added

### Service (13 tests in TestVarianceRecommendations)
- test_variance_overview, test_variance_overview_empty, test_variance_overview_outliers
- test_plan_recommendations, test_plan_recommendations_high_waste, test_plan_recommendations_high_scrap_rate, test_plan_recommendations_low_yield, test_plan_recommendations_not_found, test_plan_recommendations_no_cuts
- test_material_variance, test_material_variance_empty
- test_export_recommendations, test_export_recommendations_empty

### Router (5 tests)
- test_variance_overview, test_plan_recommendations, test_plan_recommendations_not_found_404
- test_material_variance, test_export_recommendations

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No optimization solver or BOM/manufacturing hot-path integration
