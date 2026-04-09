# Design: Manufacturing MBOM Contract Closure Audit

## Date

2026-04-03

## Scope

Audit-only. Evaluate MBOM surfaces for contract closure across CRUD
completeness, lifecycle consistency, error handling, discoverability, and
export parity.

## Surface Inventory (7 endpoints)

| # | HTTP | Path | Handler | Error handling | urls dict | Admin check | Status |
|---|------|------|---------|:-:|:-:|:-:|--------|
| M1 | POST | /mboms/from-ebom | create_mbom_from_ebom | YES | YES | YES | COMPLETE |
| M2 | GET | /mboms | list_mboms | — | NO | NO | COMPLETE |
| M3 | GET | /mboms/{id} | get_mbom | YES (404) | YES | NO | COMPLETE |
| M4 | PUT | /mboms/{id}/release | release_mbom | YES | YES | YES | COMPLETE |
| M5 | GET | /mboms/{id}/release-diagnostics | get_mbom_release_diagnostics | YES (400) | YES | YES | COMPLETE |
| M6 | PUT | /mboms/{id}/reopen | reopen_mbom | YES | YES | YES | COMPLETE |
| M7 | POST | /mboms/compare | compare_ebom_mbom | NO | YES | NO | GAP-E1 |

## Audit Matrix

| Surface | Contract object | Dimension | Status | Gap? | Gap type | Fix needed |
|---------|----------------|-----------|:------:|:----:|----------|------------|
| M1 Create | from-ebom with transformation rules | field parity | COMPLETE | NO | — | — |
| M2 List | query by source_item_id | field parity | COMPLETE | NO | — | — |
| M3 Get | full structure with operations | field parity | COMPLETE | NO | — | — |
| M4 Release | validates via ruleset | lifecycle | COMPLETE | NO | — | — |
| M5 Diagnostics | errors/warnings/ruleset | lifecycle | COMPLETE | NO | — | — |
| M6 Reopen | released → draft | lifecycle | COMPLETE | NO | — | — |
| M7 Compare | EBOM vs MBOM diff | error handling | PARTIAL | YES | tiny (GAP-E1) | ~2 LOC try/except |
| M2 List | — | discoverability | ABSENT | YES | medium (GAP-D1) | product decision |
| All | — | export | ABSENT | YES | medium (GAP-X1) | product decision |

## Gap Details

### GAP-E1: Missing error handling on compare endpoint (tiny)

`compare_ebom_mbom` handler (line 445-452) calls service directly without
try/except ValueError → HTTPException wrapping. If either EBOM item or MBOM
is not found, the ValueError propagates as a 500 instead of 400/404.

Fix: ~2 LOC (add try/except with `_raise_http_for_value_error`).

### GAP-D1: No discoverability on list endpoint (medium, product decision)

`GET /mboms` returns a raw list without `urls` dict. Other MBOM endpoints
(create, get, release, diagnostics, reopen, compare) DO return `urls` dicts.
This is the only MBOM endpoint missing it.

Assessment: Minor inconsistency within the MBOM cluster itself. Low priority.

### GAP-X1: No export endpoints (medium, product decision)

Same pattern as routing/workcenter — manufacturing module has no export.
Product decision, not a code defect.

## Discoverability Analysis

Notable: MBOM endpoints ARE more discoverability-rich than routing/workcenter.
5 of 7 endpoints return `urls` dicts (create, get, release, diagnostics,
reopen, compare). Only `list_mboms` is missing it. This is a stronger
discoverability posture than routing (which has zero).

## Classification

### **DOCS-ONLY CANDIDATE** (with 1 tiny code fix option)

| Item | Classification |
|------|---------------|
| GAP-E1 (compare error handling) | Tiny code fix (~2 LOC) |
| GAP-D1 (list discoverability) | Product decision — low priority |
| GAP-X1 (export) | Product decision — not required for closure |

## Minimum Write Set (if proceeding)

| Package | Scope | LOC | Risk |
|---------|-------|:---:|------|
| GAP-E1 micro-fix | Add try/except to compare handler | ~2 | Low |

## Surfaces Confirmed Complete After Audit

- MBOM create from EBOM: COMPLETE (with transformation rules, admin check, urls)
- MBOM list: COMPLETE (direct query, source_item_id filter)
- MBOM get: COMPLETE (full structure, error handling, urls)
- MBOM release lifecycle (release + diagnostics + reopen): COMPLETE
- MBOM compare: COMPLETE except error handling (GAP-E1)
- Admin authorization: All write/lifecycle operations enforce `_ensure_admin`
- Error handling: 5/7 endpoints complete (list needs none; compare = GAP-E1)
