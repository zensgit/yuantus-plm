# Development Report - Where-Used UI Payload

Date: 2026-01-11

## Goal
Make where-used responses UI-friendly by including standardized BOM line fields
and recursion metadata.

## Changes Delivered
- where-used entries now include:
  - `child` (queried item),
  - `line` and `line_normalized` fields (quantity/uom/find_num/effectivity, etc.)
- where-used response now echoes `recursive` and `max_levels`.
- Added verification script `scripts/verify_where_used_ui.sh`.
- Documented verification in `docs/VERIFICATION.md`.

## Files Touched
- `src/yuantus/meta_engine/services/bom_service.py`
- `src/yuantus/meta_engine/web/bom_router.py`
- `scripts/verify_where_used_ui.sh`
- `docs/VERIFICATION.md`
