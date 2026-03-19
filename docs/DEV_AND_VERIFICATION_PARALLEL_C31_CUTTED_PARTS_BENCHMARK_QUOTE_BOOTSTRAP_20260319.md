# C31 -- Cutted Parts Benchmark / Quote Bootstrap -- Dev & Verification

## Status
- complete

## Branch
- Base: `feature/claude-greenfield-base-5`
- Branch: `feature/claude-c31-cutted-parts-benchmark`

## Expected Changed Files
1. `src/yuantus/meta_engine/cutted_parts/service.py`
2. `src/yuantus/meta_engine/web/cutted_parts_router.py`
3. `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
4. `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
5. `docs/DESIGN_PARALLEL_C31_*`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C31_*`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Notes
- Keep all edits inside the isolated `cutted_parts` domain.
- Do not register the router in `app.py`.
