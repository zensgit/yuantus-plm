# C20 – PLM Box Analytics / Export Bootstrap – Dev & Verification

## Status
- planned_ready_for_claude

## Branch
- Base: `feature/claude-greenfield-base-2`
- Branch: `feature/claude-c20-box-analytics`

## Scope
- `src/yuantus/meta_engine/box/`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/meta_engine/tests/test_box_*.py`

## Verification Required
1. `pytest src/yuantus/meta_engine/tests/test_box_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`
