# Development Report - Docs + ECO UI Summary

Date: 2026-01-11

## Goal
Expose document lifecycle and ECO approval summaries inside product detail
payloads for UI aggregation.

## Changes Delivered
- Added optional `document_summary` and `eco_summary` to `/products/{item_id}`.
- Document summary aggregates related document states and sample list.
- ECO summary reports state counts, pending approvals, and last applied ECO.
- Added verification script `scripts/verify_docs_eco_ui.sh`.
- Documented verification in `docs/VERIFICATION.md`.

## Files Touched
- `src/yuantus/meta_engine/services/product_service.py`
- `src/yuantus/meta_engine/web/product_router.py`
- `scripts/verify_docs_eco_ui.sh`
- `docs/VERIFICATION.md`
