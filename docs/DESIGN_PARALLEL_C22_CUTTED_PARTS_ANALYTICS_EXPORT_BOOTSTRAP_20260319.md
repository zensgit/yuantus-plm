# C22 – Cutted Parts Analytics / Export Bootstrap – Design

## Goal
- 在独立 `cutted_parts` 子域内补第二阶段 analytics / waste / export 能力。
- 保持 `C19` 的 greenfield 隔离，不接入 `app.py`。

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Deliverables
- cut plan overview analytics
- material usage / waste summary helpers
- export-ready plan summary payload
- router-level analytics/export endpoints

## API Surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/cutted-parts/overview` | Plan counts, state breakdown, totals |
| GET | `/cutted-parts/materials/analytics` | Material breakdown by type, stock, cost |
| GET | `/cutted-parts/plans/{plan_id}/waste-summary` | Per-plan waste/utilization summary |
| GET | `/cutted-parts/export/overview` | Export-ready overview + material analytics |
| GET | `/cutted-parts/export/waste` | Export-ready waste summary across all plans |

## Service Methods (C22 additions)

1. **`overview()`** – aggregates all CutPlans: total, by_state, parts/ok/scrap/rework totals
2. **`material_analytics()`** – RawMaterial breakdown: by_type, active count, stock, cost value
3. **`waste_summary(plan_id)`** – per-plan waste detail: cut status counts, scrap weight, utilization %
4. **`export_overview()`** – combined overview + material_analytics
5. **`export_waste()`** – iterates all plans, collects scrap/waste metrics per plan

## Bug Fix
- `create_material()` now explicitly sets `is_active=True` so ORM constructor matches Column default behavior in both real DB and mock contexts.

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 BOM/manufacturing hot paths
- 不做 optimization solver
