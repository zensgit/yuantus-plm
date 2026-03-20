# C44 Dev & Verification: PLM Box Dwell / Aging Bootstrap

## Planned Changed Files
- `src/yuantus/meta_engine/box/service.py` - 4 new methods (C44 section)
- `src/yuantus/meta_engine/web/box_router.py` - 4 new endpoints (C44 section)
- `src/yuantus/meta_engine/tests/test_box_service.py` - C44 test class
- `src/yuantus/meta_engine/tests/test_box_router.py` - C44 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_box_*.py -v
bash scripts/check_allowed_paths.sh --mode staged
git diff --check
```

## Planned Coverage
- dwell_overview: with data, empty, bucket distribution
- aging_summary: with data, empty
- box_aging: with contents, empty, not found
- export_aging: with data, empty
- Router: all 4 endpoints + 404 case

## Codex Integration Target
- candidate stack branch: `feature/codex-c44c45-staging`
- Claude branch baseline: `feature/claude-greenfield-base-10`
