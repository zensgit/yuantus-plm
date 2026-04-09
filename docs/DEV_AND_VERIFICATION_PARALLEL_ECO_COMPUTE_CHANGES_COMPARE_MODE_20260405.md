# Verification: ECO Compute Changes Compare Mode

## Date

2026-04-05

## Scope

Verified compare-mode-aware ECO `compute-changes` router/service behavior. No
schema changes or migrations were introduced in this package.

## Commands

1. `pytest -q src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py -k 'compute_changes or compare_mode or eco'`
   Result: `9 passed`
2. `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile src/yuantus/meta_engine/services/eco_service.py src/yuantus/meta_engine/web/eco_router.py src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py`
   Result: `clean`
3. `git diff --check`
   Result: `clean`

## Outcome

- router forwards optional `compare_mode`
- invalid compare mode maps to `400`
- service compare-aware path builds `ECOBOMChange` rows from compare diff
- legacy no-compare-mode behavior remains intact
