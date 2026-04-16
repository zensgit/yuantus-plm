## P2-3.1 PR-2 Dashboard Export Review

Date: 2026-04-16

### Conclusion

No new blockers found. PR-2 is acceptable.

### Verified

1. Export uses the same item query surface as the dashboard item list.
   - `src/yuantus/meta_engine/services/eco_service.py`
   - `export_dashboard_items(...)` delegates to `get_approval_dashboard_items(...)`
   - This avoids a second counting/filtering path.

2. CSV columns are fixed and deterministic via `_EXPORT_COLUMNS`.

3. Router contract is correct for the intended API surface:
   - `GET /api/v1/eco/approvals/dashboard/export`
   - `fmt=json|csv`
   - bad format -> `400`
   - response sets `Content-Disposition`

### Verification Run

Focused export suite:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py
```

Result: `11 passed, 1 warning`

Related slice:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "dashboard or export or escalat or auto_assign or approval_routing or entity_type or request_create_and_list"
```

Result: `86 passed, 21 deselected, 1 warning`

### Residual Notes

1. Service-level `export_dashboard_items(fmt=...)` does not itself reject unknown formats; the router enforces `400`.
2. HTTP export tests patch the service layer, so route coverage is contract-oriented rather than end-to-end data-driven.
