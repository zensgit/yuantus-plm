# C25 - Cutted Parts Cost / Utilization Bootstrap - Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-3`
- Branch: `feature/claude-c25-cutted-parts-costing`

## Verification Required
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`
