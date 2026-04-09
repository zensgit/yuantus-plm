# Governance Contract Surpass — Reading Guide

## Date

2026-03-31

## Purpose

This document serves as a navigation index for all governance contract surpass
work completed in the C13 subcontracting parallel track. It maps each work
package to its design/verification documents and identifies the key files
involved.

## How to read this guide

1. Start with the **Final Summary** for the big picture
2. Use the **Work Package Index** to find specific topics
3. Each work package links to a design doc (why) and a verification doc (proof)

## Final Summary

- Design: `docs/DESIGN_PARALLEL_C13_SUBCONTRACTING_GOVERNANCE_CONTRACT_SURPASS_FINAL_SUMMARY_20260330.md`
- Verification: `docs/DEV_AND_VERIFICATION_PARALLEL_C13_SUBCONTRACTING_GOVERNANCE_CONTRACT_SURPASS_FINAL_SUMMARY_20260330.md`

## Work Package Index

### Phase 1: Naming & Shape Alignment

| # | Package | Design | Verification |
|---|---------|--------|-------------|
| 1 | queue_origin_rows naming | `DESIGN_..._QUEUE_ORIGIN_ROWS_NAMING_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._QUEUE_ORIGIN_ROWS_NAMING_CONTRACT_SURPASS_20260330.md` |
| 2 | comparison_summary contract | `DESIGN_..._SUMMARY_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._SUMMARY_CONTRACT_SURPASS_20260330.md` |
| 3 | queue/state breakdown alignment | `DESIGN_..._QUEUE_STATE_SUMMARY_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._QUEUE_STATE_SUMMARY_CONTRACT_SURPASS_20260330.md` |

### Phase 2: Row Drill-down Contracts

| # | Package | Design | Verification |
|---|---------|--------|-------------|
| 4 | follow_through_state_rows promotion | `DESIGN_..._QUEUE_STATE_SUMMARY_CONTRACT_SURPASS_20260330.md` (same doc, second phase) | same |
| 5 | follow_through_state drilldown (filter + URLs) | `DESIGN_..._FOLLOW_THROUGH_STATE_ROW_DRILLDOWN_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._FOLLOW_THROUGH_STATE_ROW_DRILLDOWN_CONTRACT_SURPASS_20260330.md` |
| 6 | Row follow_through_state propagation | `DESIGN_..._ACCEPTANCE_ROW_FOLLOW_THROUGH_STATE_PROPAGATION_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._ACCEPTANCE_ROW_FOLLOW_THROUGH_STATE_PROPAGATION_SURPASS_20260330.md` |

### Phase 3: Scope Parity Audits

| # | Package | Design | Verification |
|---|---------|--------|-------------|
| 7 | Snapshot scope: follow_through_state | `DESIGN_..._SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` |
| 8 | Snapshot scope: acceptance_action | `DESIGN_..._ACCEPTANCE_ACTION_SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._ACCEPTANCE_ACTION_SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` |
| 9 | Snapshot scope: acceptance_status | `DESIGN_..._ACCEPTANCE_STATUS_SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._ACCEPTANCE_STATUS_SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` |
| 10 | Snapshot scope: selection_mode | `DESIGN_..._SELECTION_MODE_SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._SELECTION_MODE_SNAPSHOT_SCOPE_PARITY_CONTRACT_SURPASS_20260330.md` |

### Phase 4: Closure Audits

| # | Package | Design | Verification |
|---|---------|--------|-------------|
| 11 | Acceptance plane closure | `DESIGN_..._ACCEPTANCE_PLANE_CLOSURE_AUDIT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._ACCEPTANCE_PLANE_CLOSURE_AUDIT_SURPASS_20260330.md` |
| 12 | Non-acceptance plane closure | `DESIGN_..._NON_ACCEPTANCE_PLANE_CLOSURE_AUDIT_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._NON_ACCEPTANCE_PLANE_CLOSURE_AUDIT_SURPASS_20260330.md` |

### Phase 5: Polish

| # | Package | Design | Verification |
|---|---------|--------|-------------|
| 13 | Markdown comparison_summary | `DESIGN_..._MARKDOWN_COMPARISON_SUMMARY_SURPASS_20260330.md` | `DEV_AND_VERIFICATION_..._MARKDOWN_COMPARISON_SUMMARY_SURPASS_20260330.md` |

## Key Source Files

| File | Role |
|------|------|
| `src/yuantus/meta_engine/subcontracting/service.py` | Service layer: filters, aggregation, row construction, export rendering |
| `src/yuantus/meta_engine/web/subcontracting_router.py` | Router: endpoint handlers, URL decoration, payload pass-through |
| `src/yuantus/meta_engine/web/subcontracting_governance_row_discoverability.py` | URL builders: snapshot URLs, row drill-down URLs, scope-aware query assembly |

## Key Test Files

| File | Coverage |
|------|----------|
| `src/yuantus/meta_engine/tests/test_subcontracting_service.py` | Service-level: filter behavior, payload shape, export formats |
| `src/yuantus/meta_engine/tests/test_subcontracting_router.py` | Router-level: endpoint integration, URL decoration, assert_called_once_with |
| `src/yuantus/meta_engine/tests/test_subcontracting_governance_discoverability.py` | URL builder: scope preservation, target-aware filtering, snapshot parity |

## Surpass Points (vs reference implementation)

1. **Backend-owned contracts** — All drill-down URLs computed server-side
2. **No frontend query dependency** — Consumers follow `row.urls.<target>`
3. **Three-surface consistency** — Standalone, embedded snapshot, export JSON produce identical contracts
4. **13-scope preservation** — Every filter preserved across snapshot/row navigation
5. **Target-aware filtering** — Only supported scopes reach each target
6. **Dual-plane closure** — Both acceptance and non-acceptance planes audited to zero gaps
