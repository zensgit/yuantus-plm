# C29 -- PLM Box Capacity / Compliance Bootstrap -- Design

## Goal
- Extend the `box` sub-domain with capacity, dimensional compliance, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_service.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `capacity_overview()` | Dict | Box count, max-quantity usage, tare/gross capacity summary |
| `compliance_summary()` | Dict | Dimension/weight compliance by type/material |
| `box_capacity(box_id)` | Dict | Per-box capacity utilization and compliance detail |
| `export_capacity()` | Dict | Export-ready payload combining overview + compliance |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/capacity/overview` | `service.capacity_overview()` | -- |
| GET | `/compliance/summary` | `service.compliance_summary()` | -- |
| GET | `/items/{box_id}/capacity` | `service.box_capacity(box_id)` | ValueError -> 404 |
| GET | `/export/capacity` | `service.export_capacity()` | -- |

## Tests

### Service Tests (TestCapacityCompliance)
- test_capacity_overview
- test_capacity_overview_empty
- test_compliance_summary
- test_compliance_summary_all_compliant
- test_box_capacity
- test_box_capacity_incomplete
- test_box_capacity_not_found
- test_export_capacity

### Router Tests
- test_capacity_overview
- test_compliance_summary
- test_box_capacity
- test_box_capacity_not_found_404
- test_export_capacity

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No storage / workflow integration
