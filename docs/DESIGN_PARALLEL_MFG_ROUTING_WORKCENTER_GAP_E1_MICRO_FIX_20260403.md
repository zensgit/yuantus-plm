# Design: Manufacturing Routing GAP-E1 Micro Fix

## Date

2026-04-03

## Scope

Add missing ValueError → HTTPException error mapping to `calculate-time` and
`calculate-cost` handlers. Aligns with all other routing lifecycle handlers.

## Changes

| Handler | Before | After |
|---------|--------|-------|
| `calculate_time` | Direct service call, no try/except | Wrapped in try/except ValueError → `_raise_http_for_value_error` |
| `calculate_cost` | Direct service call, no try/except | Same pattern |

No db.commit/rollback needed (read-only calculations).

## Files Changed

| File | Change | LOC |
|------|--------|:---:|
| `manufacturing_router.py` | 2 handlers wrapped with try/except | ~6 |
| `test_manufacturing_routing_router.py` | 2 new tests for 404 on missing routing | ~30 |
