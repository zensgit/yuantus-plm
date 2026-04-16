## P2-3.1 PR-1a Filter Parse Review

Date: 2026-04-16

### Conclusion

PR-1a fixes the outstanding blocker from PR-1. No new blockers found.

### Verified

1. Invalid `deadline_from` / `deadline_to` no longer crash the route.
   - `src/yuantus/meta_engine/web/eco_router.py`
   - `_parse_deadline(...)` now converts parse failures into `HTTPException(status_code=400, ...)`

2. The new HTTP tests hit the real route path for invalid datetime inputs.
   - `src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py`
   - `test_invalid_deadline_from_returns_400`
   - `test_invalid_deadline_to_returns_400`

### Verification Run

Focused:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py
```

Result: `28 passed, 1 warning`

Related slice:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "dashboard or escalat or auto_assign or approval_routing or entity_type or request_create_and_list or export"
```

Result: `75 passed, 21 deselected, 1 warning`

### Residual Note

The route now returns `400` for invalid datetime strings via a custom parser. This is acceptable, though a future cleanup could switch to typed FastAPI datetime query params and let validation produce `422`.
