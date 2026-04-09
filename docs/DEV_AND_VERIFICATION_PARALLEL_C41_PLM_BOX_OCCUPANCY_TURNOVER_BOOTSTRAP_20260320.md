# C41 Dev & Verification: PLM Box Occupancy / Turnover Bootstrap

## Planned Changed Files
- `src/yuantus/meta_engine/box/service.py` - 4 new methods (C41 section)
- `src/yuantus/meta_engine/web/box_router.py` - 4 new endpoints (C41 section)
- `src/yuantus/meta_engine/tests/test_box_service.py` - C41 test class
- `src/yuantus/meta_engine/tests/test_box_router.py` - C41 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_box_*.py -v
bash scripts/check_allowed_paths.sh --mode staged
git diff --check
```

## Planned Coverage
- occupancy_overview: with data, empty, rate calculation
- turnover_summary: with data, empty
- box_turnover: with contents, no contents, not found
- export_turnover: with data, empty
- Router: all 4 endpoints + 404 case

## Codex Integration Target
- candidate stack branch: `feature/codex-c41c42-staging`
- Claude branch baseline: `feature/claude-greenfield-base-9`
