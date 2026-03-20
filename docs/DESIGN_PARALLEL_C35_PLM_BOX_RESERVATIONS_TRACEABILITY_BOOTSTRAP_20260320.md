# C35 -- PLM Box Reservations / Traceability Bootstrap -- Design

## Goal
- Extend the isolated `box` domain with reservation, traceability, and export-ready helpers.

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Planned API
- `GET /api/v1/box/reservations/overview`
- `GET /api/v1/box/traceability/summary`
- `GET /api/v1/box/items/{box_id}/reservations`
- `GET /api/v1/box/export/traceability`

## Planned Service Methods
- `reservations_overview()` -- Fleet-wide reservation/load summary
- `traceability_summary()` -- Traceability coverage and orphaned-content summary
- `box_reservations(box_id)` -- Per-box reservation detail
- `export_traceability()` -- Export-ready combined payload

## Constraints
- No `app.py` registration.
- No storage, CAD, or workflow hot-path integration.
- Stay inside the isolated `box` domain.
