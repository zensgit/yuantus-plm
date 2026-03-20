# C37 -- Cutted Parts Thresholds / Envelopes Bootstrap -- Dev & Verification

## Status
- complete

## Branch
- Base: `feature/claude-greenfield-base-7`
- Branch: `feature/claude-c37-cutted-parts-thresholds`

## Changed Files
1. `src/yuantus/meta_engine/cutted_parts/service.py`
2. `src/yuantus/meta_engine/web/cutted_parts_router.py`
3. `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
4. `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
5. `docs/DESIGN_PARALLEL_C37_CUTTED_PARTS_THRESHOLDS_ENVELOPES_BOOTSTRAP_20260320.md`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C37_CUTTED_PARTS_THRESHOLDS_ENVELOPES_BOOTSTRAP_20260320.md`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v` -- `137 passed`
2. `git diff --check` -- clean
3. 22 new C37 tests added (16 service + 6 router)

## Notes
- Keep all edits inside the isolated `cutted_parts` domain.
- Do not register the router in `app.py`.

## Codex Integration Verification
- candidate stack branch: `feature/codex-c35c36c37-staging`
- cherry-pick source: `3fa66fa`
- integrated commit: `f15ad29`
- combined regression with `C35/C36`:
  - `364 passed, 130 warnings in 8.36s`
- unified stack script on staging:
  - `582 passed, 204 warnings in 13.39s`
- `git diff --check`: passed
