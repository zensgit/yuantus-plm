# C28 -- Cutted Parts Templates / Scenarios Bootstrap -- Dev & Verification

## Status
- complete

## Branch
- Base: `feature/claude-greenfield-base-4`
- Branch: `feature/claude-c28-cutted-parts-scenarios`

## Expected Changed Files
1. `src/yuantus/meta_engine/cutted_parts/service.py`
2. `src/yuantus/meta_engine/web/cutted_parts_router.py`
3. `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
4. `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
5. `docs/DESIGN_PARALLEL_C28_*`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C28_*`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Test Results
```bash
pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v
82 passed
```

## Codex Integration Verification
- candidate stack branch: `feature/codex-c26c27c28-staging`
- cherry-pick source: `13c8c90`
- integrated commit: `fabc2b5`
- combined regression with `C26+C27`:
  - `222 passed, 82 warnings in 3.75s`
- unified stack script on staging:
  - `440 passed, 156 warnings in 13.91s`
- `git diff --check`: passed

## Notes
- Keep all edits inside the isolated `cutted_parts` domain.
- Do not register the router in `app.py`.
