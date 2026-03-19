# C20 – PLM Box Analytics / Export Bootstrap – Dev & Verification

## Status
- completed

## Branch
- Base: `feature/claude-greenfield-base-2`
- Branch: `feature/claude-c20-box-analytics`

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Files Modified
| File | Change |
|------|--------|
| `src/yuantus/meta_engine/box/service.py` | Added 5 analytics/export methods |
| `src/yuantus/meta_engine/web/box_router.py` | Added 5 new endpoints |
| `src/yuantus/meta_engine/tests/test_box_service.py` | Added TestBoxAnalytics (8 tests) |
| `src/yuantus/meta_engine/tests/test_box_router.py` | Added 7 analytics/export endpoint tests |

## Test Results
```
34 passed in 3.70s
```

### Service Tests (20 total: 12 C17 + 8 C20)
- TestBoxCRUD: 5 (C17)
- TestBoxState: 4 (C17)
- TestBoxContents: 3 (C17)
- TestBoxAnalytics: 8 (C20) — overview, overview_empty, material_analytics, contents_summary, contents_summary_not_found, export_overview, export_contents, export_contents_not_found

### Router Tests (14 total: 7 C17 + 7 C20)
- C17: create_item, list_items, get_item, get_contents, export_meta, not_found_404, create_invalid_400
- C20: overview, material_analytics, contents_summary, contents_summary_not_found_404, export_overview, export_contents, export_contents_not_found_404

## Verification Required
1. `pytest src/yuantus/meta_engine/tests/test_box_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Codex Integration Verification
- candidate stack branch: `feature/codex-stack-c20c21`
- cherry-pick source: `4102f55`
- integrated commit: `e85d046`
- combined regression with `C21`:
  - `83 passed, 33 warnings in 9.00s`
- `git diff --check`: passed
