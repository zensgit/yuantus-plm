# Dev And Verification - Parallel ECO Suspended State And Actions

## Date

2026-04-06

## Files

- `src/yuantus/meta_engine/models/eco.py`
- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

## Verification

1. `pytest -q src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py -k 'suspend or unsuspend or move_to_stage or apply or approve or reject'`
   - `16 passed, 2 deselected`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/models/eco.py src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/web/eco_router.py src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
   - clean
3. `git diff --check`
   - clean

## Notes

- No production behavior outside suspend/unsuspend lifecycle was changed
- Existing apply and compare-mode coverage remained green in the focused ECO test slice
