# P2-3.1 PR-3: Approval Ops Audit — Development & Verification

**Branch:** feature/claude-c43-cutted-parts-throughput
**Date:** 2026-04-16
**Status:** ✅ 241 passed, 0 failed (8 focused audit tests)

---

## Scope

轻量异常读面。告诉运营"为什么卡住"，不是模板系统。

---

## Endpoint

```
GET /api/v1/eco/approvals/audit/anomalies
```

返回：

```json
{
  "no_candidates": [
    {
      "eco_id": "e1", "eco_name": "ECO-1",
      "stage_id": "s1", "stage_name": "Review",
      "approval_roles": ["specialist"],
      "reason": "no active users with matching active roles"
    }
  ],
  "escalated_unresolved": [
    {
      "eco_id": "e2", "eco_name": "ECO-2",
      "stage_id": "s1", "stage_name": "Review",
      "admin_user_id": 99, "admin_username": "admin",
      "approval_id": "a1"
    }
  ],
  "overdue_not_escalated": [
    {
      "eco_id": "e3", "eco_name": "ECO-3",
      "stage_id": "s2", "stage_name": "Final",
      "hours_overdue": 8.0,
      "reason": "overdue but no escalation triggered"
    }
  ],
  "total_anomalies": 3
}
```

---

## Three Anomaly Types

| Category | Meaning | Data Source |
|---|---|---|
| `no_candidates` | Stage requires approval but `_resolve_candidate_users` returns empty | Active ECO × stage (approval_type != none) |
| `escalated_unresolved` | Admin-escalated ECOApproval still pending | ECOApproval.required_role == "admin" + status == pending |
| `overdue_not_escalated` | Overdue (deadline passed) but no admin escalation exists | `list_overdue_approvals()` × no ECOApproval with required_role=admin |

---

## Files Changed

| File | Change |
|---|---|
| `services/eco_service.py` | `get_approval_anomalies()` |
| `web/eco_router.py` | `GET /approvals/audit/anomalies` |
| `tests/test_eco_approval_audit.py` | **新建** — 8 focused tests |

---

## Focused Tests (8)

```
TestNoCandidates (2)
  test_detected_when_no_active_users_match              PASSED
  test_not_flagged_when_candidates_exist                PASSED

TestEscalatedUnresolved (1)
  test_detected_when_admin_pending                      PASSED

TestOverdueNotEscalated (2)
  test_detected_when_overdue_and_no_admin_approval      PASSED
  test_not_flagged_when_admin_exists                    PASSED

TestTotalAnomalies (1)
  test_total_is_sum                                     PASSED

TestAuditHTTP (2)
  test_route_registered                                 PASSED
  test_returns_200_with_shape                           PASSED
```

---

## Verification

```bash
# PR-3 focused
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_audit.py -v
# Expected: 8 passed

# Full P2-3.1 suite (PR-1 + PR-2 + PR-3)
python3 -m pytest \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py \
  -v
# Expected: 47 passed

# Full regression
python3 -m pytest src/yuantus/meta_engine/tests/ -q
# Expected: 241 passed
```

---

## P2-3.1 Complete

| PR | Content | Tests |
|---|---|---|
| PR-1 + PR-1a | Dashboard filters (company, eco_type, state, deadline range) + input validation | 28 |
| PR-2 | Dashboard export (CSV + JSON) | 11 |
| PR-3 | Approval ops audit (anomalies) | 8 |
| **Total** | | **47** |
