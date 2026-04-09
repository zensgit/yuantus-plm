# ECO BOM Compare Mode Integration — Reading Guide

## Date

2026-04-05

## Who this is for

An engineer or reviewer encountering the ECO/BOM compare-mode integration line
for the first time.

## Recommended Reading Paths

### Shortest path (2 docs, ~10 min)

1. **Final Summary** — closure state, fixed gaps, no blocking items
2. **Integration Audit Design** — original gap matrix and package split

### Full implementation path (6 docs, ~20 min)

1. Final Summary (design + verification)
2. Integration Audit (design + verification)
3. Compute Changes Compare Mode (design + verification)
4. Compare Mode Contract Tests (design + verification)

## Document Map by Topic

### 1. Final Summary & Closure

*Answers: "Is the line closed? What exactly was fixed?"*

| Doc | Path |
| --- | --- |
| Final Summary Design | `docs/DESIGN_PARALLEL_ECO_BOM_COMPARE_MODE_INTEGRATION_FINAL_SUMMARY_20260405.md` |
| Final Summary Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_BOM_COMPARE_MODE_INTEGRATION_FINAL_SUMMARY_20260405.md` |
| Integration Audit Design | `docs/DESIGN_PARALLEL_ECO_BOM_COMPARE_MODE_INTEGRATION_AUDIT_20260405.md` |
| Integration Audit Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_BOM_COMPARE_MODE_INTEGRATION_AUDIT_20260405.md` |

### 2. Compute Changes Compare Mode

*Answers: "How did `compute-changes` become compare-mode aware?"*

| Doc | Path |
| --- | --- |
| Package Design | `docs/DESIGN_PARALLEL_ECO_COMPUTE_CHANGES_COMPARE_MODE_20260405.md` |
| Package Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_COMPUTE_CHANGES_COMPARE_MODE_20260405.md` |

### 3. Compare Mode Contract Tests

*Answers: "Which ECO routes now have explicit compare-mode contract coverage?"*

| Doc | Path |
| --- | --- |
| Package Design | `docs/DESIGN_PARALLEL_ECO_COMPARE_MODE_CONTRACT_TESTS_20260405.md` |
| Package Verification | `docs/DEV_AND_VERIFICATION_PARALLEL_ECO_COMPARE_MODE_CONTRACT_TESTS_20260405.md` |

## Surface Guide

### BOM Compare Base Surfaces

Use the integration audit to orient the already-mature BOM compare family:

- raw compare
- delta preview/export
- summarized compare/export/snapshots

### ECO Read-Side Compare Mode Surfaces

Use the integration audit plus contract tests to understand:

- `GET /eco/{eco_id}/impact`
- `GET /eco/{eco_id}/impact/export`
- `GET /eco/{eco_id}/bom-diff`

### ECO Mutation-Side Compare Mode Surface

Use the compute-changes package to understand:

- `POST /eco/{eco_id}/compute-changes`

This is the only surface that needed real functional closure work.

## Key Source Files

| File | Role |
| --- | --- |
| `src/yuantus/meta_engine/services/bom_service.py` | compare mode registry and compare output shape |
| `src/yuantus/meta_engine/services/eco_service.py` | ECO compare-mode integration and compute-changes mapping |
| `src/yuantus/meta_engine/web/bom_router.py` | BOM compare router contract |
| `src/yuantus/meta_engine/web/eco_router.py` | ECO compare-mode router contract |

## Key Test Files

| File | Coverage |
| --- | --- |
| `src/yuantus/meta_engine/tests/test_bom_delta_preview.py` | compare output -> delta preview |
| `src/yuantus/meta_engine/tests/test_bom_delta_router.py` | delta export router |
| `src/yuantus/meta_engine/tests/test_bom_summarized_router.py` | summarized compare router |
| `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py` | compute-changes router contract |
| `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py` | compare-aware compute-changes service behavior |
| `src/yuantus/meta_engine/tests/test_eco_compare_mode_router.py` | focused compare-mode router contract tests |

## Remaining Items

No known blocking gaps remain for the ECO BOM compare mode integration line.
