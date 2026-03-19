# C23 -- PLM Box Ops Report / Transitions Bootstrap -- Design

## Goal
- Extend the `box` sub-domain (C17 baseline + C20 analytics) with ops-report
  and state-transition read helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_service.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`

## New Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `transition_summary()` | Dict | Total count, by_state breakdown, draft-to-active and active-to-archive eligible counts |
| `active_archive_breakdown()` | Dict | Active vs archived groups with count, total_cost, by_type detail |
| `ops_report(box_id)` | Dict | Per-box info + can_activate/can_archive/is_terminal flags + contents count |
| `export_ops_report()` | Dict | Combined transition_summary + active_archive_breakdown payload |

## New API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/transitions/summary` | `service.transition_summary()` | -- |
| GET | `/active-archive/breakdown` | `service.active_archive_breakdown()` | -- |
| GET | `/items/{box_id}/ops-report` | `service.ops_report(box_id)` | ValueError -> 404 |
| GET | `/export/ops-report` | `service.export_ops_report()` | -- |

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No CAD / storage / workflow integration
