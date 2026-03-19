# C22 – Cutted Parts Analytics / Export Bootstrap – Dev & Verification

## Status
- planned_ready_for_claude

## Branch
- Base: `feature/claude-greenfield-base-2`
- Branch: `feature/claude-c22-cutted-parts-analytics`

## Scope
- `src/yuantus/meta_engine/cutted_parts/`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_*.py`

## Verification Required
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`
