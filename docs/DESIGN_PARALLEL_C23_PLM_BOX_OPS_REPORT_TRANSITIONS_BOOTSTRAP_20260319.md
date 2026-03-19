# C23 - PLM Box Ops Report / Transitions Bootstrap - Design

## Goal
Extend the isolated `box` domain with ops-report and state-transition read helpers without touching `app.py` or any cross-domain hot path.

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Suggested Deliverables
- state transition summary helper
- active/archive breakdown helper
- export-ready ops report payload
- router-level ops/export endpoints

## Non-Goals
- no app registration
- no storage/CAD/version/parallel_tasks integration
- no workflow orchestration
