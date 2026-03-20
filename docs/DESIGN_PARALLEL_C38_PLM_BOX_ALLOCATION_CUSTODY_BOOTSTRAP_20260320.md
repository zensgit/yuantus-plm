# C38 -- PLM Box Allocation / Custody Bootstrap -- Design

## Goal
- Extend the isolated `box` domain with allocation, custody, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Planned API
- `GET /api/v1/box/allocations/overview`
- `GET /api/v1/box/custody/summary`
- `GET /api/v1/box/items/{box_id}/custody`
- `GET /api/v1/box/export/custody`

## Planned Service Methods
- `allocations_overview()` -- Fleet-wide allocation and assignment summary
- `custody_summary()` -- Custody completeness and handoff summary
- `box_custody(box_id)` -- Per-box custody detail
- `export_custody()` -- Export-ready combined payload

## Constraints
- No `app.py` registration.
- No storage, CAD, or workflow hot-path integration.
- Stay inside the isolated `box` domain.
