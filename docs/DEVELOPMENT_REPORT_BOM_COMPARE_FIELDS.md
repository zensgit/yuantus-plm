# Development Report - BOM Compare Field Contract

Date: 2026-01-11

## Goal
Provide a stable, UI-friendly field contract for BOM compare output, including
normalized line fields for quantity, position, effectivity, and substitutes.

## Changes Delivered
- Added standard line fields to BOM compare output:
  - Added/Removed entries now return `line` + `line_normalized`.
  - Changed entries now return `before_line/after_line` and
    `before_normalized/after_normalized`.
- Ensured normalized fields are JSON-safe (tuples converted to lists).
- Added verification script `scripts/verify_bom_compare_fields.sh`.
- Documented the verification command in `docs/VERIFICATION.md`.

## Field Contract (Summary)
Standard line fields available in compare output:
`quantity`, `uom`, `find_num`, `refdes`,
`effectivity_from`, `effectivity_to`, `effectivities`, `substitutes`.

Raw properties remain in `properties`, while normalized values are exposed in
`line_normalized` (added/removed) or `before_normalized/after_normalized`
(changed).

## Files Touched
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `scripts/verify_bom_compare_fields.sh`
- `docs/VERIFICATION.md`
