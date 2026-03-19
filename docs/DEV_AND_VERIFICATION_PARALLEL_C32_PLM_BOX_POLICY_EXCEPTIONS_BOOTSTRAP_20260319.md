# C32 -- PLM Box Policy / Exceptions Bootstrap -- Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-6`
- Branch: `feature/claude-c32-box-policy`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_box_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`
