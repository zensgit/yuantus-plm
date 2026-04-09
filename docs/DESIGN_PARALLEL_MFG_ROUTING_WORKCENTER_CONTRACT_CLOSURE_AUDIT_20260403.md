# Design: Manufacturing Routing / WorkCenter Contract Closure Audit

## Date

2026-04-03

## Scope

Audit-only. Evaluate routing + workcenter surfaces for contract closure across
CRUD completeness, lifecycle consistency, error handling, discoverability, and
export parity.

## Surface Inventory

### Routing (15 endpoints)

| # | HTTP | Path | Handler | Error handling | Status |
|---|------|------|---------|:-:|--------|
| R1 | POST | /routings | create_routing | YES | COMPLETE |
| R2 | GET | /routings | list_routings | — | COMPLETE |
| R3 | GET | /routings/{id} | get_routing | YES | COMPLETE |
| R4 | PUT | /routings/{id}/primary | set_primary_routing | YES | COMPLETE |
| R5 | GET | /routings/{id}/operations | list_operations | YES | COMPLETE |
| R6 | POST | /routings/{id}/operations | add_operation | YES | COMPLETE |
| R7 | PATCH | /routings/{id}/operations/{op_id} | update_operation | YES | COMPLETE |
| R8 | DELETE | /routings/{id}/operations/{op_id} | delete_operation | YES | COMPLETE |
| R9 | POST | /routings/{id}/operations/resequence | resequence_operations | YES | COMPLETE |
| R10 | POST | /routings/{id}/calculate-time | calculate_time | NO | GAP-E1 |
| R11 | POST | /routings/{id}/calculate-cost | calculate_cost | NO | GAP-E1 |
| R12 | PUT | /routings/{id}/release | release_routing | YES | COMPLETE |
| R13 | GET | /routings/{id}/release-diagnostics | get_release_diagnostics | YES | COMPLETE |
| R14 | PUT | /routings/{id}/reopen | reopen_routing | YES | COMPLETE |
| R15 | POST | /routings/{id}/copy | copy_routing | YES | COMPLETE |

### WorkCenter (4 endpoints)

| # | HTTP | Path | Handler | Error handling | Status |
|---|------|------|---------|:-:|--------|
| W1 | POST | /workcenters | create_workcenter | YES | COMPLETE |
| W2 | GET | /workcenters | list_workcenters | — | COMPLETE |
| W3 | GET | /workcenters/{id} | get_workcenter | YES | COMPLETE |
| W4 | PATCH | /workcenters/{id} | update_workcenter | YES | COMPLETE |

## Audit Matrix

| Surface | Contract object | Dimension | Status | Gap? | Gap type | Fix needed |
|---------|----------------|-----------|:------:|:----:|----------|------------|
| R1-R3 Routing CRUD | create/list/get | field parity | COMPLETE | NO | — | — |
| R4 Primary | set_primary | lifecycle | COMPLETE | NO | — | — |
| R5-R9 Operation CRUD | add/list/patch/delete/resequence | lifecycle | COMPLETE | NO | — | — |
| R10-R11 Calculate | time/cost | error handling | PARTIAL | YES | tiny (GAP-E1) | ~4 LOC try/except |
| R12-R14 Release lifecycle | release/diagnostics/reopen | lifecycle | COMPLETE | NO | — | — |
| R15 Copy | copy_routing | lifecycle | COMPLETE | NO | — | — |
| W1-W4 WorkCenter CRUD | create/list/get/patch | field parity | COMPLETE | NO | — | — |
| All surfaces | — | discoverability (urls dict) | ABSENT | YES | medium (GAP-D1) | ~60 LOC |
| All surfaces | — | export parity | ABSENT | YES | medium (GAP-X1) | ~80 LOC per surface |

## Gap Details

### GAP-E1: Missing error handling on calculate-time and calculate-cost (tiny)

`calculate_time` and `calculate_cost` handlers call service methods directly
without try/except ValueError → HTTPException wrapping. All other write/compute
endpoints have this. Fix: ~4 LOC (2 per handler).

### GAP-D1: No discoverability / urls dict on any surface (medium)

No endpoint returns a `urls` dict. The subcontracting module has comprehensive
HATEOAS discoverability. The manufacturing module has none. This is
architecturally consistent within the manufacturing module (it was built as
simple REST CRUD without discoverability), but inconsistent with the
subcontracting standard.

**Assessment**: This is a product decision, not a code bug. Manufacturing
surfaces are simpler (single-entity CRUD) and clients navigate via REST
conventions. Adding discoverability would be ~60 LOC but provides marginal
value for CRUD-only surfaces.

### GAP-X1: No export endpoints (medium)

No routing or workcenter surface has export (JSON/CSV/Markdown). The
subcontracting module has export on every read surface. Manufacturing has none.

**Assessment**: Also a product decision. Manufacturing data is small-cardinality
(routings × operations, workcenters). Export may not be needed unless operators
want offline review of routing configurations.

## Classification

### **DOCS-ONLY CANDIDATE** (with 1 tiny code fix option)

The manufacturing routing/workcenter cluster is functionally complete for its
design scope. The gaps are:

1. **GAP-E1** (tiny, ~4 LOC): Missing try/except on 2 calculate endpoints.
   Could be fixed in a micro-fix package.
2. **GAP-D1** (medium, product decision): No discoverability. Not a bug —
   architectural choice. Add only if product requires it.
3. **GAP-X1** (medium, product decision): No export. Not a bug — add only
   if operators need offline routing review.

**No new discoverability layer required for closure.** The manufacturing module
is a different architectural pattern (simple CRUD) from the subcontracting
module (complex governance + operational surfaces with HATEOAS).

## Minimum Write Set (if proceeding)

| Package | Scope | LOC | Risk |
|---------|-------|:---:|------|
| GAP-E1 micro-fix | Add try/except to calculate-time + calculate-cost | ~4 | Low |
| GAP-D1 (optional) | Add urls dict to routing GET/list and workcenter GET/list | ~60 | Low |
| GAP-X1 (optional) | Add export for routing list + workcenter list | ~80 each | Low |

## Surfaces Confirmed Complete After Audit

- Routing CRUD (create, list, get): COMPLETE
- Operation lifecycle (add, list, patch, delete, resequence): COMPLETE
- Routing lifecycle (primary, release, diagnostics, reopen, copy): COMPLETE
- WorkCenter CRUD (create, list, get, patch): COMPLETE
- Error handling: 17/19 endpoints (2 missing = GAP-E1)
- Admin authorization: All write operations enforce `_ensure_admin`
