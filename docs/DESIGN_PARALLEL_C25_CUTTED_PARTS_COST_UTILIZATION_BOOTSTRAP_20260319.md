# C25 - Cutted Parts Cost / Utilization Bootstrap - Design

## Goal
Extend the isolated `cutted_parts` domain with cost and utilization read helpers without coupling the increment to BOM or manufacturing hot paths.

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Suggested Deliverables
- utilization summary helper
- cost summary helper
- export-ready cost/utilization payload
- router-level analytics/export endpoints

## Non-Goals
- no app registration
- no optimization solver
- no BOM/manufacturing hot-path integration
