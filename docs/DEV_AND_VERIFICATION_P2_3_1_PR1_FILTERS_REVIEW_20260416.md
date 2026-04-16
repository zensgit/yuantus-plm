## P2-3.1 PR-1 Filters Review

Date: 2026-04-16

### Conclusion

Do not move to PR-2 yet. PR-1 still needs one small hardening fix.

### Findings

1. High: invalid `deadline_from` / `deadline_to` values currently raise an unhandled `ValueError` in the router.
   - Files:
     - `src/yuantus/meta_engine/web/eco_router.py:361-377`
     - `src/yuantus/meta_engine/web/eco_router.py:387-405`
   - Current implementation parses query params manually with `datetime.fromisoformat(...)`.
   - Example reproduction:
     - `GET /api/v1/eco/approvals/dashboard/summary?deadline_from=not-a-date`
   - Result:
     - route raises `ValueError: Invalid isoformat string`
     - this becomes a server exception instead of a clean `400/422`

2. Medium: new filter tests are mostly signature/forwarding checks, not data-driven filtering semantics.
   - File:
     - `src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py`
   - Missing coverage examples:
     - `company_id` actually narrows rows
     - `eco_type` actually narrows rows
     - `deadline_from/deadline_to` actually narrows rows
     - invalid datetime query returns controlled client error

### What Was Verified

1. The previous two blockers remain fixed:
   - current-stage binding is enforced in `_base_dashboard_query()`
   - summary and items share the same base approval-row scope

2. Focused test results:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py
```

Result: `26 passed, 1 warning`

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  -k "dashboard or escalat or auto_assign or approval_routing or entity_type or request_create_and_list or export"
```

Result: `73 passed, 21 deselected, 1 warning`

3. Runtime reproduction of the invalid datetime issue:

```bash
PYTHONPATH=src python3 - <<'PY'
from src.yuantus.meta_engine.tests.test_eco_approval_dashboard import TestDashboardHTTP
client, db = TestDashboardHTTP()._client()
client.get('/api/v1/eco/approvals/dashboard/summary?deadline_from=not-a-date')
PY
```

Observed:
- unhandled `ValueError: Invalid isoformat string: 'not-a-date'`

### Recommended Next Step

Ship a tiny `PR-1a` first:

1. Change `deadline_from` / `deadline_to` router params to typed `datetime` query params, or catch parse failures explicitly.
2. Ensure invalid values return `422` (preferred via FastAPI validation) or `400`.
3. Add two HTTP tests:
   - invalid `deadline_from`
   - invalid `deadline_to`

After that, move to PR-2.
