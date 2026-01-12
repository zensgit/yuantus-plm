# Development Report - Product UI Aggregation

Date: 2026-01-11

## Goal
Extend product detail payloads to include lightweight BOM and where-used
summaries so UI can render key counts without extra round trips.

## Changes Delivered
- Added BOM summary and where-used summary options to `/products/{item_id}`.
- Added query controls for summary depth and recursion.
- Added verification script `scripts/verify_product_ui.sh`.
- Documented verification in `docs/VERIFICATION.md`.

## Output (Summary)
When enabled, the response includes:
- `bom_summary`: `authorized`, `depth`, `direct_children`, `total_children`, `max_depth`
- `where_used_summary`: `authorized`, `count`, `recursive`, `max_levels`, `sample`

## Files Touched
- `src/yuantus/meta_engine/services/product_service.py`
- `src/yuantus/meta_engine/web/product_router.py`
- `scripts/verify_product_ui.sh`
- `docs/VERIFICATION.md`
