# C38 -- PLM Box Allocation / Custody Bootstrap -- Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-8`
- Branch: `feature/claude-c38-box-custody`

## Planned Verification
1. `pytest src/yuantus/meta_engine/tests/test_box_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Notes
- Codex integration verification will be added after Claude completes the branch.
- Do not register the router in `app.py`.
