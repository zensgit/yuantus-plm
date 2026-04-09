# Manufacturing Routing / WorkCenter Contract Surpass — Reading Guide

## Date

2026-04-03

## Who this is for

An engineer or reviewer encountering the manufacturing routing / workcenter
contract surpass line for the first time.

---

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — all 19 endpoints, gap history, zero blocking gaps
2. **Closure Audit Design** — the full surface×dimension matrix

### Full audit path (4 docs, ~20 min)

1. Final Summary (design + verification)
2. Closure Audit (design + verification)
3. GAP-E1 Micro-Fix (design + verification)

---

## Document Map by Topic

### 1. Final Summary & Closure

*Answers: "Is the cluster complete? What gaps were found and fixed?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_SURPASS_FINAL_SUMMARY_20260403.md` |
| Closure Audit Design | `docs/DESIGN_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_CLOSURE_AUDIT_20260403.md` |
| Closure Audit Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_MFG_ROUTING_WORKCENTER_CONTRACT_CLOSURE_AUDIT_20260403.md` |

### 2. GAP-E1 Micro-Fix

*Answers: "How was the calculate error handling gap fixed?"*

| Doc | Path |
|-----|------|
| Micro-Fix Design | `docs/DESIGN_PARALLEL_MFG_ROUTING_WORKCENTER_GAP_E1_MICRO_FIX_20260403.md` |
| Micro-Fix Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_MFG_ROUTING_WORKCENTER_GAP_E1_MICRO_FIX_20260403.md` |

### 3. Routing CRUD

*Answers: "How do routing create/list/get work?"*

Covered in closure audit §Audit Matrix (R1-R3). Key: create returns Routing
entity, list supports mbom_id/item_id filters, get is direct DB lookup.

### 4. Operation Lifecycle

*Answers: "How do add/patch/delete/resequence work for operations?"*

Covered in closure audit §Audit Matrix (R5-R9). Key: full CRUD on operations
within a routing, resequence reorders by provided ID list.

### 5. Release / Release-Diagnostics / Reopen / Copy

*Answers: "How does the routing release lifecycle work?"*

Covered in closure audit §Audit Matrix (R12-R15). Key: release validates via
diagnostics ruleset, reopen reverses release, copy creates a new routing from
an existing one.

### 6. WorkCenter CRUD

*Answers: "How do workcenter create/list/get/update work?"*

Covered in closure audit §Audit Matrix (W1-W4). Key: CRUD with plant_code
filter on list, include_inactive flag, update via PATCH.

### 7. Remaining Non-Blocking Items / Product Decisions

*Answers: "What was audited and intentionally left out?"*

- **GAP-D1 (discoverability)**: No HATEOAS urls dict. Product decision — manufacturing is simple CRUD, not governance+operational.
- **GAP-X1 (export)**: No JSON/CSV/Markdown export. Product decision — small-cardinality data.
- Both can be added later if product requirements change.

---

## Key Source Files

| File | Role |
|------|------|
| `src/yuantus/meta_engine/web/manufacturing_router.py` | All routing + workcenter endpoints |
| `src/yuantus/meta_engine/manufacturing/routing_service.py` | Routing + operation business logic |
| `src/yuantus/meta_engine/manufacturing/workcenter_service.py` | WorkCenter CRUD logic |

## Key Test Files

| File | Coverage |
|------|----------|
| `test_manufacturing_routing_router.py` | Router-level: error mapping, calculate handlers |
| `test_manufacturing_routing_lifecycle.py` | Service-level: release/reopen/copy lifecycle |
| `test_manufacturing_routing_primary.py` | Primary routing selection |
| `test_manufacturing_routing_workcenter_validation.py` | WorkCenter validation in operations |
| `test_manufacturing_workcenter_router.py` | WorkCenter router endpoints |
| `test_manufacturing_workcenter_service.py` | WorkCenter service CRUD |
| `test_manufacturing_release_diagnostics.py` | Release diagnostics ruleset |

## Note on `...` abbreviations

Paths use `..._` to abbreviate `PARALLEL_MFG`. Full filenames in
`docs/DELIVERY_DOC_INDEX.md`.
