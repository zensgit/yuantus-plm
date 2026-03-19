# C34 -- Cutted Parts Variance / Recommendations Bootstrap -- Design

## Goal
- Extend the isolated `cutted_parts` domain with variance, recommendation, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Suggested API
- `GET /api/v1/cutted-parts/variance/overview`
- `GET /api/v1/cutted-parts/plans/{plan_id}/recommendations`
- `GET /api/v1/cutted-parts/materials/variance`
- `GET /api/v1/cutted-parts/export/recommendations`

## Constraints
- No `app.py` registration.
- No optimization solver.
- Stay inside the isolated `cutted_parts` domain.
