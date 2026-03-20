# C40 -- Cutted Parts Alerts / Outliers Bootstrap -- Dev & Verification

## Status
- complete

## Branch
- Base: `feature/claude-greenfield-base-8`
- Branch: `feature/claude-c40-cutted-parts-alerts`

## Changed Files
1. `src/yuantus/meta_engine/cutted_parts/service.py`
2. `src/yuantus/meta_engine/web/cutted_parts_router.py`
3. `src/yuantus/meta_engine/tests/test_cutted_parts_service.py`
4. `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
5. `docs/DESIGN_PARALLEL_C40_CUTTED_PARTS_ALERTS_OUTLIERS_BOOTSTRAP_20260320.md`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C40_CUTTED_PARTS_ALERTS_OUTLIERS_BOOTSTRAP_20260320.md`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_cutted_parts_*.py -v` -- `158 passed`
2. `git diff --check` -- clean
3. 21 new C40 tests added (16 service + 5 router)

## Notes
- Keep all edits inside the isolated `cutted_parts` domain.
- Do not register the router in `app.py`.

## Codex Integration Verification
- candidate stack branch: `feature/codex-c38c39c40-staging`
- cherry-pick source: `3a543bf`
- integrated commit: `d789b72`
- combined regression with `C38/C39`:
  - `417 passed, 146 warnings in 7.52s`
- unified stack script on staging:
  - `635 passed, 220 warnings in 14.02s`
- `git diff --check`: passed
