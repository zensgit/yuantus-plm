# Design: ECO Activity Chain → Release Readiness Linkage Audit

## Date

2026-04-06

## Scope

Audit the linkage between ECO activity chain (task gates) and release readiness
(apply diagnostics) to confirm the dual-layer readiness architecture is complete.

## Architecture: Dual-Layer Readiness

```
Layer 1: Activity Chain (ECOActivityGate)
  └── Sequential task gates with dependency blocking
  └── blockers_for_eco() → _ensure_activity_gate_ready()

Layer 2: Release Readiness (get_apply_diagnostics)
  └── Rule-based pre-flight checks via ValidationIssue
  └── ReleaseDiagnosticsResponse contract
```

Both layers coupled through `_ensure_activity_gate_ready()` which blocks
critical transitions (apply, unsuspend, move_to_stage).

## Linkage Matrix

| Transition | Activity gate check? | Diagnostics available? | Custom actions? | Status |
|-----------|:---:|:---:|:---:|--------|
| `action_apply` | YES (`_ensure_activity_gate_ready`) | YES (`get_apply_diagnostics`) | YES (before/after) | COMPLETE |
| `move_to_stage` | YES | — | YES (before/after) | COMPLETE |
| `action_unsuspend` | YES | YES (`get_unsuspend_diagnostics`) | — | COMPLETE |
| `approve/reject` | — | — | — | COMPLETE (no gate needed) |

## Activity Gate Model

| Component | Status | Evidence |
|-----------|:------:|---------|
| `ECOActivityGate` model (id, eco_id, status, is_blocking, depends_on_activity_ids) | IMPLEMENTED | models line 59 |
| `ECOActivityGateEvent` audit trail (from_status, to_status, reason, user_id) | IMPLEMENTED | models line 82 |
| `ECOActivityValidationService.blockers_for_eco()` | IMPLEMENTED | parallel_tasks_service line 1544 |
| `_ensure_activity_gate_ready()` in ECOService | IMPLEMENTED | eco_service line 132 |
| Dependency chain resolution (`_dependency_blockers`) | IMPLEMENTED | parallel_tasks_service line 1219 |
| Status state machine (pending→active→completed/canceled/exception) | IMPLEMENTED | parallel_tasks_service transitions dict |

## Release Readiness Rules (apply diagnostics)

| Rule | Code | Validation |
|------|------|-----------|
| eco.exists | `eco_not_found` | ECO must exist |
| eco.state_approved | `eco_not_approved` | State must be "approved" |
| eco.required_fields | `eco_missing_fields` | product_id + target_version_id set |
| eco.product_exists | `product_not_found` | Product item exists |
| eco.target_version_exists | `target_version_missing` | Target version exists |
| eco.rebase_conflicts | `rebase_conflicts` | No conflicts (unless ignore_conflicts) |

## API Surface

| HTTP | Path | Purpose | Status |
|------|------|---------|--------|
| GET | /eco/{id}/apply-diagnostics | Pre-apply validation | COMPLETE |
| POST | /eco/{id}/apply | Execute apply | COMPLETE |
| GET | /eco/{id}/unsuspend-diagnostics | Pre-unsuspend validation | COMPLETE |
| POST | /eco/{id}/move-stage | Stage transition | COMPLETE |

## Test Coverage

| Test file | What it covers |
|-----------|---------------|
| `test_eco_apply_diagnostics.py` | Diagnostics 200/400, permission gate, force bypass, suspend/unsuspend |
| `test_eco_parallel_flow_hooks.py` | Activity gate + custom action hooks in move_to_stage |

## Audit Findings

### Linkage status: IMPLEMENTED AND COMPLETE

The dual-layer architecture is fully wired:
- Activity gates block transitions via `_ensure_activity_gate_ready()`
- Release diagnostics surface issues via `get_apply_diagnostics()`
- Both are exposed through REST API with `ReleaseDiagnosticsResponse`
- Custom action hooks fire before/after transitions
- Approval SLA is enforced via `_apply_stage_sla()`

### Minor observations (non-blocking)

1. No dedicated diagnostic rule for `ECOState.CONFLICT` — conflicts are checked
   via `rebase_conflicts_absent` rule but not via a state-level rule
2. No explicit notification on activity gate status changes (only stage assignment
   notifications exist)

## Classification

**TINY CODE GAP — fixed by `eco-apply-diagnostics-activity-gate-rule` package.**

`get_apply_diagnostics()` was missing the `eco.activity_blockers_clear` rule.
Fixed by adding the rule to the default ruleset and the handler. Now closure-ready.
