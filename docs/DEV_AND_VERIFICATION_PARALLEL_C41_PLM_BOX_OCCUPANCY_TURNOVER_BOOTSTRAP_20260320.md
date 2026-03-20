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
