# C44 Dev & Verification: PLM Box Dwell / Aging Bootstrap

## Changed Files
- `src/yuantus/meta_engine/box/service.py` — 4 new methods (C44 section)
- `src/yuantus/meta_engine/web/box_router.py` — 4 new endpoints (C44 section)
- `src/yuantus/meta_engine/tests/test_box_service.py` — TestDwellAging class (12 tests)
- `src/yuantus/meta_engine/tests/test_box_router.py` — 6 C44 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_box_*.py -v
git diff --check
```

## Test Coverage
- dwell_overview: with data, empty, high/low dwell detection
- aging_summary: with data, empty, all tiers
- box_aging: with items, no items, not found (ValueError)
- export_aging: with data, empty
- Router: all 4 endpoints + 404 case for box_aging

## Codex Integration Target
- candidate stack branch: `feature/codex-c44c45-staging`
- Claude branch baseline: `feature/claude-greenfield-base-10`
