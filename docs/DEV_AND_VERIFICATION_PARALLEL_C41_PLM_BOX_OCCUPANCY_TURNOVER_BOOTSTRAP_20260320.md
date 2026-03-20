# Dev & Verification: C41 PLM Box Occupancy / Turnover Bootstrap

## Changed Files
- `src/yuantus/meta_engine/box/service.py` — 4 new methods
- `src/yuantus/meta_engine/web/box_router.py` — 4 new endpoints
- `src/yuantus/meta_engine/tests/test_box_service.py` — ~11 new service tests
- `src/yuantus/meta_engine/tests/test_box_router.py` — 5 new router tests

## Verification
```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_box_service.py -v
python3 -m pytest src/yuantus/meta_engine/tests/test_box_router.py -v
git diff --check
```

## Codex Integration Verification
- candidate stack branch: `feature/codex-c41c42-staging`
- cherry-pick source: `f1fcb43`
- integrated commit: `f8c9753`
- combined regression with `C42`:
  - `291 passed, 110 warnings in 3.37s`
- unified stack script on staging:
  - `667 passed, 231 warnings in 13.47s`
- `git diff --check`: passed
