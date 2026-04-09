# Workflow Custom Action Predicate Upgrade — Reading Guide

## Date

2026-04-06

## Who this is for

An engineer or reviewer encountering the workflow custom action predicate
upgrade for the first time.

---

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — what was done, architectural decisions, zero gaps
2. **Predicate Upgrade Audit** — what existed before, what was missing

### Full implementation path (6 docs, ~30 min)

1. Final Summary (design + verification)
2. Predicate Upgrade Audit (design + verification)
3. Runtime Scope Predicates (design + verification)
4. Context Predicates and Tests (design + verification)

---

## Document Map by Topic

### 1. Final Summary

*Answers: "Is the upgrade complete? What predicates are available?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_..._PREDICATE_UPGRADE_FINAL_SUMMARY_20260406.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_..._PREDICATE_UPGRADE_FINAL_SUMMARY_20260406.md` |

### 2. Predicate Upgrade Audit

*Answers: "What was the existing execution model? What was missing?"*

| Doc | Path |
|-----|------|
| Audit Design | `docs/DESIGN_..._PREDICATE_UPGRADE_AUDIT_20260405.md` |
| Audit Verification | `docs/DEV_AND_VERIFICATION_..._PREDICATE_UPGRADE_AUDIT_20260405.md` |

### 3. Runtime Scope Predicates

*Answers: "How do workflow_map_id, stage_id, eco_priority matching work?"*

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_..._RUNTIME_SCOPE_PREDICATES_20260405.md` |
| Verification | `docs/DEV_AND_VERIFICATION_..._RUNTIME_SCOPE_PREDICATES_20260405.md` |

### 4. Context Predicates and Tests

*Answers: "How do actor_roles, product_id, eco_type matching work? What tests lock the contract?"*

| Doc | Path |
|-----|------|
| Design | `docs/DESIGN_..._CONTEXT_PREDICATES_AND_TESTS_20260406.md` |
| Verification | `docs/DEV_AND_VERIFICATION_..._CONTEXT_PREDICATES_AND_TESTS_20260406.md` |

### 5. Execution Model / Fail Strategies / Ordering

Covered in the audit design doc. Key points:
- Actions execute in `priority` order
- Predicates filter (skip) but don't reorder
- Fail-closed on missing context (action skipped)
- No rollback on predicate skip (idempotent)

### 6. ECO Hook Integration

The predicates integrate with ECO workflow hooks. `eco_priority` and `eco_type`
are evaluated using data from the ECO context passed into the custom action
evaluator. See runtime scope predicates design for integration details.

### 7. Remaining Non-Goals / Guardrails

- **No generic predicate DSL** — deliberate. Each predicate is a named field.
- **No compound expressions** — no AND/OR trees. Multiple predicates on one
  action are implicitly AND (all must match).
- **No time-based predicates** — not needed for current use cases. Can be added
  as a named field later without architectural change.
- **No dynamic predicate loading** — predicates are defined at action creation
  time, not at execution time.

---

## Key Source Files

| File | Role |
|------|------|
| Custom action evaluator service | Predicate matching + execution |
| Workflow transition hooks | ECO context injection |
| Custom action model | Predicate field definitions |

## Note on `...` abbreviations

Paths use `..._` to abbreviate `PARALLEL_WORKFLOW_CUSTOM_ACTION`. Full
filenames in `docs/DELIVERY_DOC_INDEX.md`.
