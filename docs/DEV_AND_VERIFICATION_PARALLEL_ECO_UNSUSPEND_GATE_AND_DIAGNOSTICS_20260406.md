# Dev And Verification - Parallel ECO Unsuspend Gate And Diagnostics

## Date

2026-04-06

## Files

- `src/yuantus/meta_engine/services/eco_service.py`
- `src/yuantus/meta_engine/web/eco_router.py`
- `src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`
- `src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`

## Verification

1. `pytest -q src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py -k 'suspend or unsuspend or move_to_stage or apply or approve or reject or diagnostics'`
   - `21 passed, 2 deselected`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/web/eco_router.py src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py`
   - clean
3. `git diff --check`
   - clean

## Notes

- Default unsuspend behavior is now gated
- `force=true` remains available for explicit override
- No unrelated ECO mutation or export behavior changed
