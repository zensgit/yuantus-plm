# C34 -- Cutted Parts Variance / Recommendations Bootstrap -- Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-6`
- Branch: `feature/claude-c34-cutted-parts-variance`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`
