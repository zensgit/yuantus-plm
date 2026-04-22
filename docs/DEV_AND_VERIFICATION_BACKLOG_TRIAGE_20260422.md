# Backlog Triage

Date: 2026-04-22

## 1. Goal

Categorize items carried forward after the CAD router decomposition closeout.

This document is a decision table only. It does not introduce runtime code, tests, ops tooling, or feature behavior.

## 2. Inputs

Reviewed sources:

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md`
- `docs/DEV_AND_VERIFICATION_POST_CAD_ROUTER_DECOMPOSITION_CLOSEOUT_20260422.md`
- `docs/DEV_AND_VERIFICATION_ODOO18_GAP_CYCLE_CLOSEOUT_20260421.md`
- current `main` after PR #366

## 3. Triage Table

| Item | Current state | Action | Reason |
| --- | --- | --- | --- |
| BOM router decomposition | `bom_router.py` remains a large router hotspot at about 2146 LOC | do | Highest-value architecture follow-up after CAD and parallel task router decomposition; first slice should be taskbook + BOM compare split. |
| Scheduler infrastructure and consumers | Scheduler foundation, dry-run, audit retention, ECO escalation, BOM-to-MBOM handlers, and local activation suites exist; scheduler remains default-off | wait-for-external-signal | More ops investment should wait for a real pilot owner, pilot environment, and operations commitment. |
| Scheduler production decision gate | Plan calls for explicit go / no-go within 30 days | do | Needed to stop open-ended scheduler planning; should decide between production rehearsal and default-off maintenance. |
| UOM transformation rules granularity | UOM-aware write/read/compare/report surfaces are closed; EBOM-to-MBOM transformation rules still apply by item id | dormant | Registered as a low-priority semantic extension; implement only when operations needs UOM-specific exclude/substitute rules. |
| CadImportService extraction | `cad_import_router.py` owns import route but still contains about 924 LOC of business logic | dormant | Useful architecture cleanup, but lower priority than BOM router decomposition because import route is already isolated and contract-covered. |
| Shared-dev 142 real observations | Existing workflow and readonly smoke paths exist; no new shared-dev signal in this triage step | wait-for-external-signal | Do not run bootstrap or fabricate observations; use readonly evidence only when credentials and execution window are explicitly available. |
| UI / frontend change requests | BOM Diff UI, CAD Viewer, and approval UI remain possible future work | wait-for-external-signal | No immediate customer-visible pull signal was provided in this cycle; keep backend-first discipline. |
| `cad_router.py` compatibility shell removal | `cad_router.py` is 23 LOC and owns zero routes | dormant | Removal is a compatibility cleanup with low ROI; keep until a dedicated cleanup PR updates ownership contracts. |
| MES / sales / procurement expansion | Explicitly outside current mainline scope | delete | Do not carry as backlog in this cycle; it conflicts with the Part / BOM / Rev / ECO / Doc / CAD scope discipline. |

## 4. Immediate Decision

The next implementation track should be:

1. External signal collection summary.
2. BOM router decomposition taskbook.
3. BOM compare split as the first bounded implementation slice.

Scheduler production work should not continue as more ops tooling until the decision gate has a real pilot commitment.

## 5. Verification

Documentation-only change. Required verification:

```bash
git diff --check

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```
