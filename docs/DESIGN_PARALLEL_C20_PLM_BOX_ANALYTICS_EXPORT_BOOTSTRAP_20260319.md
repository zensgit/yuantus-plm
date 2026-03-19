# C20 – PLM Box Analytics / Export Bootstrap – Design

## Goal
- 在独立 `box` 子域内补第二阶段 analytics / export 能力。
- 保持 `C17` 的 greenfield 隔离，不接入 `app.py`。

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Deliverables
- box overview / analytics read model
- material / state breakdown helpers
- export-ready overview payload
- router-level export endpoints

## Suggested API
- `GET /api/v1/box/overview`
- `GET /api/v1/box/materials/analytics`
- `GET /api/v1/box/items/{box_id}/contents-summary`
- `GET /api/v1/box/export/overview`
- `GET /api/v1/box/items/{box_id}/export-contents`

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 `parallel_tasks` / `version` / `benchmark_branches`
- 不做 CAD / storage / workflow integration
