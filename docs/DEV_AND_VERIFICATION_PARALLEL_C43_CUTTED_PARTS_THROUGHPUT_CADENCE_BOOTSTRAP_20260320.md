# C43 Dev & Verification: Cutted Parts Throughput / Cadence Bootstrap

## Planned Changed Files
- `src/yuantus/meta_engine/cutted_parts/service.py` - 4 new methods (C43 section)
- `src/yuantus/meta_engine/web/cutted_parts_router.py` - 4 new endpoints (C43 section)
- `src/yuantus/meta_engine/tests/test_cutted_parts_service.py` - C43 test class
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py` - C43 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v
bash scripts/check_allowed_paths.sh --mode staged
git diff --check
```

## Planned Coverage
- throughput_overview: with data, empty, avg throughput
- cadence_summary: with data, empty
- plan_cadence: with cuts, empty plan, not found
- export_cadence: with data, empty
- Router: all 4 endpoints + 404 case

## Codex Integration Target
- candidate stack branch: `feature/codex-c41c42-staging`
- Claude branch baseline: `feature/claude-greenfield-base-9`
