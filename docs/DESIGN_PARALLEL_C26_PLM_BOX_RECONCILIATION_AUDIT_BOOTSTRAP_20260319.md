# C26 -- PLM Box Reconciliation / Audit Bootstrap -- Design

## Goal
- Extend the `box` sub-domain with reconciliation, audit, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_service.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`

## Implemented Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `reconciliation_overview()` | Dict | Fleet-wide completeness: barcode/dimensions/weight coverage, completeness_pct |
| `audit_summary()` | Dict | Data quality: boxes missing material/dimensions/cost, archived-with-contents |
| `box_reconciliation(box_id)` | Dict | Per-box: 5 completeness checks, contents count, total quantity |
| `export_box_reconciliation()` | Dict | Export-ready payload combining overview + audit summary |

## Implemented API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/reconciliation/overview` | `service.reconciliation_overview()` | -- |
| GET | `/audit/summary` | `service.audit_summary()` | -- |
| GET | `/items/{box_id}/reconciliation` | `service.box_reconciliation(box_id)` | ValueError -> 404 |
| GET | `/export/reconciliation` | `service.export_box_reconciliation()` | -- |

## Tests
- Service: 8 tests in `TestReconciliationAudit` class
- Router: 5 tests for all C26 endpoints

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No storage / workflow / CAD integration
