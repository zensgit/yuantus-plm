# Phase 3 Progress Snapshot (2026-02-06)

## 1. Scope

This snapshot records current implementation status for roadmap section
`Phase 3: MBOM and Routing`, based on code in `main` and merged PRs up to
`2026-02-06`.

## 2. Completed

### 2.1 MBOM and routing baseline capability

- MBOM creation from EBOM, structure query, and EBOM/MBOM compare exist.
- Routing baseline capability exists: create routing, add operations, time/cost
  estimate, and copy routing.

### 2.2 Day 1-3 delivered increments

- Day 1: WorkCenter service + API skeleton (CRUD list/get/create/update).
- Day 2: WorkCenter guardrails:
  - operation-to-workcenter validation,
  - admin-only write for WorkCenter APIs.
- Day 3: Strong operation association:
  - `workcenter_id` + backward-compatible `workcenter_code`,
  - id/code consistency checks,
  - operation API request/response aligned.

Reference reports:
- `docs/DEV_AND_VERIFICATION_P3_DAY1_WORKCENTER_20260206.md`
- `docs/DEV_AND_VERIFICATION_P3_DAY2_WORKCENTER_GUARDRAILS_20260206.md`
- `docs/DEV_AND_VERIFICATION_P3_DAY3_WORKCENTER_ASSOC_20260206.md`

## 3. Pending (Day 4+ focus)

- Primary routing lifecycle:
  - keep single primary routing per scope (`item_id` or `mbom_id`),
  - explicit API to switch primary routing.
- Routing query ergonomics:
  - list routings by `item_id` / `mbom_id` for client-side selection.
- Follow-up candidate slices:
  - operation edit/resequence/delete lifecycle,
  - release/status flow for routing and MBOM.

## 4. Risks

- Multiple primary routings can cause ambiguous routing selection in MBOM
  operation attachment and downstream manufacturing calculations.
- Missing routing list/primary APIs increases client-side workarounds and
  potential data inconsistency.
- Permission boundary for routing write actions should stay explicit to avoid
  accidental widening.

## 5. Current branch objective

Branch `codex/phase3-day4-routing-primary-20260206` implements Day 4 as:

- single-primary guarantee in routing scope,
- primary-switch API,
- routing list API,
- automated verification (pytest + Playwright),
- development and verification report.
