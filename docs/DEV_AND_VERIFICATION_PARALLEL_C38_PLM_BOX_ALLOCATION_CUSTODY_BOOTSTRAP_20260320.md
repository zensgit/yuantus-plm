# C38 Dev & Verification: PLM Box Allocation / Custody Bootstrap

## Changed Files
- `src/yuantus/meta_engine/box/service.py` - 4 new methods (C38 section)
- `src/yuantus/meta_engine/web/box_router.py` - 4 new endpoints (C38 section)
- `src/yuantus/meta_engine/tests/test_box_service.py` - TestAllocationsCustody class
- `src/yuantus/meta_engine/tests/test_box_router.py` - 5 endpoint tests (C38 section)

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_box_service.py -v
python3 -m pytest src/yuantus/meta_engine/tests/test_box_router.py -v
git diff --check
```

## Test Coverage
- allocations_overview: with data, empty, allocation rate
- custody_summary: with data, empty
- box_custody: with contents, no contents, not found
- export_custody: with data, empty
- Router: all 4 endpoints + 404 case
