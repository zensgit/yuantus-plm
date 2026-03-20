# C46 Dev & Verification: Cutted Parts Saturation / Bottlenecks Bootstrap

## Planned Changed Files
- `src/yuantus/meta_engine/cutted_parts/service.py` - 4 new methods (C46 section)
- `src/yuantus/meta_engine/web/cutted_parts_router.py` - 4 new endpoints (C46 section)
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py` - C46 test class
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py` - C46 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v
bash scripts/check_allowed_paths.sh --mode staged
git diff --check
```

## Planned Coverage
- saturation_overview: with data, empty, bucket distribution
- bottlenecks_summary: with data, empty
- plan_bottlenecks: with cuts, no cuts, not found
- export_bottlenecks: with data, empty
- Router: all 4 endpoints + 404 case

## Codex Integration Target
- candidate stack branch: `feature/codex-c44c45-staging`
- Claude branch baseline: `feature/claude-greenfield-base-10`
