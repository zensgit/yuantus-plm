# P2 Dev Observation Startup Checklist

**Date:** 2026-04-16
**Main baseline:** `49ff1c3` (PR #220 + #221 merged)

---

## Baseline Test Status

```
273 passed, 0 failed
2026-04-16 replay remediation applied
```

### Replay Remediation Status

| Test File | Previous Failures | Status | Resolution |
|---|---|---|
| `test_eco_parallel_flow_hooks.py` | 15 | ✅ Fixed | hook `context`, suspend guards, compare_mode support restored |
| `test_eco_apply_diagnostics.py` | 5 | ✅ Fixed | suspend/unsuspend routes, diagnostics, apply lock guards restored |

**Owner:** Codex remediation complete  
**Impact on P2:** None — P2 approval/dashboard/audit tests still pass after replay remediation

**Reference:** `docs/DEV_AND_VERIFICATION_ECO_PARALLEL_FLOW_HOOK_REPLAY_REMEDIATION_20260416.md`

---

## Checklist

| # | Item | Status |
|---|---|---|
| 1 | Main baseline confirmed (`49ff1c3`) | ✅ |
| 2 | P2 endpoints exist on main (6/6) | ✅ |
| 3 | P2 focused tests pass (approval + dashboard + audit) | ✅ |
| 4 | Replay regressions remediated and documented | ✅ |
| 5 | Runbook available (`P2_OPS_RUNBOOK.md`) | ✅ |
| 6 | Observation template available (`P2_OPS_OBSERVATION_TEMPLATE.md`) | ✅ |
| 7 | Dev environment selected | Pending |
| 8 | Auth accounts prepared | Pending |
| 9 | Sample ECO data prepared | Pending |
| 10 | Baseline observation recorded | Pending |
| 11 | 3 event types exercised | Pending |
| 12 | Weekly cadence confirmed | Pending |

---

## Verification Command

```bash
# Replay remediation + diagnostics hooks
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py -q --tb=no

# P2 approval chain focused slice
python3 -m pytest src/yuantus/meta_engine/tests/test_eco_approval_auto_assign.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard.py \
  src/yuantus/meta_engine/tests/test_eco_approval_dashboard_export.py \
  src/yuantus/meta_engine/tests/test_eco_approval_audit.py -q --tb=no
```
