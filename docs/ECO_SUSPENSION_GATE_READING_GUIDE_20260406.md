# ECO Suspension Gate — Reading Guide

## Date

2026-04-06

## Who this is for

An engineer or reviewer encountering the ECO suspension gate line for the first time.

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — closure state, fixed gaps, no blocking items
2. **Suspension Gate Audit Design** — original gap matrix and package split

### Full implementation path (6 docs, ~20 min)

1. Final Summary (design + verification)
2. Suspension Gate Audit (design + verification)
3. Suspended State and Actions (design + verification)
4. Unsuspend Gate and Diagnostics (design + verification)

## Document Map by Topic

### 1. Final Summary & Closure

*Answers: "Is the line closed? What exactly was fixed?"*

| Doc | Path |
| --- | --- |
| Final Summary Design | `docs/DESIGN_PARALLEL_ECO_SUSPENSION_GATE_FINAL_SUMMARY_20260406.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_SUSPENSION_GATE_FINAL_SUMMARY_20260406.md` |
| Suspension Gate Audit Design | `docs/DESIGN_PARALLEL_ECO_SUSPENSION_GATE_AUDIT_20260406.md` |
| Suspension Gate Audit Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_SUSPENSION_GATE_AUDIT_20260406.md` |

### 2. Suspended State and Actions

*Answers: "How did ECO get an explicit suspend lifecycle?"*

| Doc | Path |
| --- | --- |
| Package Design | `docs/DESIGN_PARALLEL_ECO_SUSPENDED_STATE_AND_ACTIONS_20260406.md` |
| Package Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_SUSPENDED_STATE_AND_ACTIONS_20260406.md` |

### 3. Unsuspend Gate and Diagnostics

*Answers: "How is unsuspend gated, and what blocks resumption?"*

| Doc | Path |
| --- | --- |
| Package Design | `docs/DESIGN_PARALLEL_ECO_UNSUSPEND_GATE_AND_DIAGNOSTICS_20260406.md` |
| Package Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_UNSUSPEND_GATE_AND_DIAGNOSTICS_20260406.md` |

## Surface Guide

### Lifecycle Surfaces

Use the implementation docs to understand:

- `POST /eco/{eco_id}/suspend`
- `POST /eco/{eco_id}/unsuspend`

These are the primary lifecycle actions introduced by this line.

### Guarded ECO Mutation Surfaces

Use the suspended-state package to understand why these actions now fail while suspended:

- `move-stage`
- `new-revision`
- `approve`
- `reject`

### Operator Diagnostics Surface

Use the unsuspend diagnostics package to understand:

- `GET /eco/{eco_id}/unsuspend-diagnostics`
- default-gated `POST /eco/{eco_id}/unsuspend`
- `force=true` override behavior

## Key Source Files

| File | Role |
| --- | --- |
| `src/yuantus/meta_engine/models/eco.py` | ECO state enum and lifecycle model |
| `src/yuantus/meta_engine/services/eco_service.py` | suspend/unsuspend actions and diagnostics |
| `src/yuantus/meta_engine/web/eco_router.py` | suspend/unsuspend router contract |

## Key Test Files

| File | Coverage |
| --- | --- |
| `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py` | service-level lifecycle hooks and diagnostics behavior |
| `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py` | router diagnostics and unsuspend gate contract |

## Remaining Items

No known blocking gaps remain for the ECO suspension gate line.
