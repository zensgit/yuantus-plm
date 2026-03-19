# C17 PLM Box Bootstrap Design

## Goal
- 在独立 `box` 子域内建立 PLM Box bootstrap。

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Deliverables
- box item model
- list/detail/create bootstrap API
- export-ready metadata/read model

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 `parallel_tasks` / `version` / `benchmark_branches`
