# C26 -- PLM Box Reconciliation / Audit Bootstrap -- Design

## Goal
- Extend the `box` sub-domain with reconciliation, audit, and export-ready helpers.
- Keep greenfield isolation: no integration into `app.py`.

## Scope
- `src/yuantus/meta_engine/box/service.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_service.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`

## Suggested Service Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `reconciliation_overview()` | Dict | Total boxes, content mismatches, missing metadata, reconcilable count |
| `audit_summary()` | Dict | Count by state/type/material with transition anomalies summary |
| `box_reconciliation(box_id)` | Dict | Per-box content mismatch and missing-field detail |
| `export_reconciliation()` | Dict | Export-ready payload combining overview + audit summary |

## Suggested API Endpoints

| Method | Path | Handler | Error |
|--------|------|---------|-------|
| GET | `/reconciliation/overview` | `service.reconciliation_overview()` | -- |
| GET | `/audit/summary` | `service.audit_summary()` | -- |
| GET | `/items/{box_id}/reconciliation` | `service.box_reconciliation(box_id)` | ValueError -> 404 |
| GET | `/export/reconciliation` | `service.export_reconciliation()` | -- |

## Non-Goals
- No changes to `src/yuantus/api/app.py`
- No storage / workflow / CAD integration
