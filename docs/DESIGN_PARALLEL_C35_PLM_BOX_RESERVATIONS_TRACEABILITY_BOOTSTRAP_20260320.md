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

## Service Method Details

### reservations_overview()
Returns fleet-wide reservation metrics:
- `total`: total box count
- `by_state`: boxes grouped by state (draft/active/archived)
- `reserved`: boxes with at least one content line
- `unreserved`: boxes with no contents
- `average_fill_rate`: mean fill percentage across reserved boxes with max_quantity set

### traceability_summary()
Returns content lineage tracking metrics:
- `total_contents`: total content lines across all boxes
- `with_lot_serial` / `without_lot_serial`: content lines with/without lot/serial tracking
- `boxes_with_traceability` / `boxes_without_traceability`: boxes categorized by lot/serial presence
- `traceability_pct`: percentage of content lines with lot/serial data

### box_reservations(box_id)
Per-box reservation detail:
- Box identity fields (id, name, state)
- `contents_count`, `max_quantity`, `fill_pct`
- `lot_serial_count`, `lot_serial_pct`
- Full `contents` list with item_id, quantity, lot_serial, note

### export_traceability()
Export-ready combined payload:
- `reservations_overview`: full fleet reservation metrics
- `traceability_summary`: full traceability metrics
- `per_box_details`: list of boxes with contents including fill/lot counts

## Constraints
- No `app.py` registration.
- No storage, CAD, or workflow hot-path integration.
- Stay inside the isolated `box` domain.
