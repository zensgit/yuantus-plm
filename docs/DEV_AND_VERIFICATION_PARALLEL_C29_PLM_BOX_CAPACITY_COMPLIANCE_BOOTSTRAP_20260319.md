# C29 -- PLM Box Capacity / Compliance Bootstrap -- Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-5`
- Branch: `feature/claude-c29-box-capacity`

## Expected Changed Files
1. `src/yuantus/meta_engine/box/service.py`
2. `src/yuantus/meta_engine/web/box_router.py`
3. `src/yuantus/meta_engine/tests/test_box_service.py`
4. `src/yuantus/meta_engine/tests/test_box_router.py`
5. `docs/DESIGN_PARALLEL_C29_*`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C29_*`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_box_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Notes
- Keep all edits inside the isolated `box` domain.
- Do not register the router in `app.py`.
