# Doc-Sync Checkout Governance Enhancement — Reading Guide

## Date

2026-04-04

## Who this is for

An engineer or reviewer encountering the doc-sync checkout governance line for
the first time.

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — closed gaps, current status, remaining parked items
2. **Governance Enhancement Audit** — original matrix and split plan

### Full implementation path (8 docs, ~20 min)

1. Final Summary (design + verification)
2. Governance Enhancement Audit (design + verification)
3. Direction Filter (design + verification)
4. Warn/Block Mode (design + verification)
5. Directional Thresholds (design + verification)

## Document Map By Topic

### 1. Final Summary & Closure

*Answers: "Is the line closed? What exactly was fixed?"*

| Doc | Path |
|-----|------|
| Final Summary Design | `docs/DESIGN_PARALLEL_DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_FINAL_SUMMARY_20260404.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_FINAL_SUMMARY_20260404.md` |
| Audit Design | `docs/DESIGN_PARALLEL_DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_AUDIT_20260403.md` |
| Audit Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOC_SYNC_CHECKOUT_GOVERNANCE_ENHANCEMENT_AUDIT_20260403.md` |

### 2. Direction Filter

*Answers: "How did checkout gate become direction-aware?"*

| Doc | Path |
|-----|------|
| Direction Filter Design | `docs/DESIGN_PARALLEL_DOC_SYNC_GATE_DIRECTION_FILTER_20260403.md` |
| Direction Filter Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOC_SYNC_GATE_DIRECTION_FILTER_20260403.md` |

### 3. Warn / Block Mode

*Answers: "How does advisory mode differ from blocking mode?"*

| Doc | Path |
|-----|------|
| Warn/Block Mode Design | `docs/DESIGN_PARALLEL_DOC_SYNC_GATE_WARN_BLOCK_MODE_20260404.md` |
| Warn/Block Mode Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOC_SYNC_GATE_WARN_BLOCK_MODE_20260404.md` |

### 4. Directional Threshold Overrides

*Answers: "How are push and pull thresholds applied independently?"*

| Doc | Path |
|-----|------|
| Directional Thresholds Design | `docs/DESIGN_PARALLEL_DOC_SYNC_GATE_DIRECTIONAL_THRESHOLDS_20260404.md` |
| Directional Thresholds Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_DOC_SYNC_GATE_DIRECTIONAL_THRESHOLDS_20260404.md` |

### 5. Existing Analytics / Export Surfaces

*Answers: "Why wasn't a new analytics or export layer added?"*

Covered in the governance enhancement audit. The conclusion was that overview,
conflicts, reconciliation, freshness, watermarks, drift, lineage, and existing
exports already provide the necessary observability foundation.

### 6. Remaining Non-Blocking Items / Product Decisions

*Answers: "What was intentionally left parked?"*

- G5: push/pull conflict strategy
- G6: directional freshness enforcement
- G7: directional watermark enforcement

These were audited as future product decisions, not required for B1+B2 parity.

## Key Source Files

| File | Role |
|------|------|
| `src/yuantus/meta_engine/services/parallel_tasks_service.py` | Checkout gate evaluation and doc-sync operational summaries |
| `src/yuantus/meta_engine/web/version_router.py` | Checkout endpoint and gate integration |
| `src/yuantus/meta_engine/web/document_sync_router.py` | Existing analytics/export surfaces used by this line |
| `src/yuantus/meta_engine/document_sync/service.py` | Existing document-sync service foundation |

## Key Test Files

| File | Coverage |
|------|----------|
| `test_version_router_doc_sync_gate.py` | Router gate behavior, 409 mapping, warn-mode headers |
| `test_parallel_tasks_services.py` | Service gate logic, direction filtering, site default, threshold overrides |
| `test_document_sync_service.py` | Existing doc-sync service foundation |
| `test_document_sync_router.py` | Existing doc-sync router/export surfaces |
| `test_parallel_tasks_router.py` | Existing dead-letter/replay operational surfaces |

## Note on scope

This reading guide is only for the checkout governance enhancement line. It is
not a full guide to the entire document-sync subsystem.
