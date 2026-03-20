# C37 -- Cutted Parts Thresholds / Envelopes Bootstrap -- Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-7`
- Branch: `feature/claude-c37-cutted-parts-thresholds`

## Planned Verification
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Notes
- Codex integration verification will be added after Claude completes the branch.
- Do not register the router in `app.py`.
