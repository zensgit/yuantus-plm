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

## Suggested API
- `GET /api/v1/cutted-parts/overview`
- `GET /api/v1/cutted-parts/materials/analytics`
- `GET /api/v1/cutted-parts/plans/{plan_id}/waste-summary`
- `GET /api/v1/cutted-parts/export/overview`
- `GET /api/v1/cutted-parts/export/plans/{plan_id}`

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 BOM/manufacturing hot paths
- 不做 optimization solver
