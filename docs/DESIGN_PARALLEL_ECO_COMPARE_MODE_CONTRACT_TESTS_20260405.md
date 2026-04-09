# Design: ECO Compare Mode Contract Tests

## Date

2026-04-05

## Scope

Lock the `compare_mode` contract on 4 ECO surfaces via focused router tests.
No production code changes.

## Contract Points Locked

| # | Surface | Test | Assertion |
|---|---------|------|-----------|
| 1 | GET /eco/{id}/impact | `test_impact_passes_compare_mode_to_service` | compare_mode kwarg reaches `analyze_impact` |
| 2 | GET /eco/{id}/impact | `test_impact_invalid_compare_mode_returns_400` | ValueError → HTTP 400 |
| 3 | GET /eco/{id}/impact/export | `test_impact_export_passes_compare_mode_to_service` | compare_mode kwarg reaches `analyze_impact` via export path |
| 4 | GET /eco/{id}/bom-diff | `test_bom_diff_passes_compare_mode_to_service` | compare_mode kwarg reaches `get_bom_diff` |
| 5 | GET /eco/{id}/bom-diff | `test_bom_diff_invalid_compare_mode_returns_400` | ValueError → HTTP 400 |
| 6 | POST /eco/{id}/compute-changes | `test_compute_changes_passes_compare_mode_to_service` | compare_mode kwarg reaches `compute_bom_changes` |
| 7 | POST /eco/{id}/compute-changes | `test_compute_changes_invalid_compare_mode_returns_400` | ValueError → HTTP 400 |
| 8 | POST /eco/{id}/compute-changes | `test_compute_changes_none_compare_mode_uses_default` | compare_mode=None when omitted |

## Files Changed

| File | Change |
|------|--------|
| `test_eco_compare_mode_router.py` | NEW — 8 focused contract tests |
