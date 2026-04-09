# Dev And Verification - Parallel Doc-Sync Gate Directional Thresholds

## Date

2026-04-04

## Delivery

Implemented:

- per-direction threshold override parsing
- effective threshold selection by resolved gate direction
- router pass-through for `doc_sync_direction_thresholds`
- focused service/router coverage

## Verification

1. `pytest -q src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py src/yuantus/meta_engine/tests/test_parallel_tasks_services.py -k 'doc_sync or checkout_gate or warn_mode or direction_threshold'`
   - `14 passed, 53 deselected`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/web/version_router.py src/yuantus/meta_engine/services/parallel_tasks_service.py src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
   - passed
3. `git diff --check`
   - passed

## Notes

- base thresholds remain supported
- direction thresholds are additive overrides, not a replacement schema
- warn/block mode behavior remains unchanged by this package
