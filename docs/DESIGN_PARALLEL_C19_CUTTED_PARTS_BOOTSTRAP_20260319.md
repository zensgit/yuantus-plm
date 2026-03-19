# C19 Cutted Parts Bootstrap Design

## Goal
- 在独立 `cutted_parts` 子域内建立 cutted-parts bootstrap。

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Deliverables
- raw material / cut plan bootstrap model
- list/detail/summary read model
- export-friendly response contract

## Non-Goals
- 不改 `src/yuantus/api/app.py`
- 不改 BOM / manufacturing 热服务
