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

## New Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `overview()` | Dict | Total counts, state/type breakdowns, active count, total cost |
| `material_analytics()` | Dict | Breakdown by material value, no-material count |
| `contents_summary(box_id)` | Dict | Per-box aggregate: line count, distinct items, total qty, lot tracking |
| `export_overview()` | Dict | Combined overview + material_analytics payload |
| `export_contents(box_id)` | Dict | Contents summary + full line list for export |

## New API Endpoints

| Method | Path | Handler |
|--------|------|---------|
| GET | `/overview` | High-level box overview |
| GET | `/materials/analytics` | Material breakdown |
| GET | `/items/{box_id}/contents-summary` | Per-box contents aggregate |
| GET | `/export/overview` | Export-ready combined overview |
| GET | `/items/{box_id}/export-contents` | Export-ready contents with line details |

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 `parallel_tasks` / `version` / `benchmark_branches`
- 不做 CAD / storage / workflow integration
