# Design: Doc-Sync Gate Direction Filter

## Date

2026-04-03

## Scope

Add direction-aware filtering to checkout sync gate (G1 from enhancement audit).
Does NOT add warn/block mode or asymmetric thresholds.

## Changes

### `evaluate_checkout_sync_gate()` — direction parameter

Added `direction: Optional[str] = None`. When provided:
- Validates against `_ALLOWED_DIRECTIONS` (push/pull)
- Filters job query by exact `task_type == f"document_sync_{direction}"`
  instead of `.like("document_sync_%")`
- When `None` (default), matches all directions (backward compatible)

Added `direction` to response dict.

### Checkout handler — pass direction

Added `doc_sync_direction: Optional[str] = Body(None)` to checkout endpoint.
Passed through to `evaluate_checkout_sync_gate(direction=...)`.

## Files Changed

| File | Change | LOC |
|------|--------|:---:|
| `parallel_tasks_service.py` | direction param + validation + query filter + response field | ~15 |
| `version_router.py` | direction body param + pass-through | ~3 |
| `test_parallel_tasks_services.py` | New direction filter test (push/pull/tolerant/invalid) | ~60 |
| `test_version_router_doc_sync_gate.py` | 5 existing assertions updated with `direction=None` | ~5 |
