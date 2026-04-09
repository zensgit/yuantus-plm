# Verification: ECO Apply Diagnostics Activity Gate Rule

## Date

2026-04-06

## Test Results

```bash
pytest -q src/yuantus/meta_engine/tests/test_eco_apply_diagnostics.py \
  src/yuantus/meta_engine/tests/test_eco_parallel_flow_hooks.py \
  src/yuantus/meta_engine/tests/test_release_readiness_router.py \
  -k 'apply or diagnostics or activity_gate'
# Result: 17 passed, 10 deselected

py_compile eco_service.py test_eco_apply_diagnostics.py
# Result: clean

git diff --check
# Result: clean
```

## Checklist

- [x] `eco.activity_blockers_clear` added to ECO_APPLY_RULES_DEFAULT
- [x] Handler in get_apply_diagnostics matches unsuspend pattern
- [x] code=eco_activity_blockers_present, rule_id=eco.activity_blockers_clear
- [x] action_apply runtime gate unchanged
- [x] New test locks structured error contract
- [x] 17 focused tests pass (`10 deselected`)
