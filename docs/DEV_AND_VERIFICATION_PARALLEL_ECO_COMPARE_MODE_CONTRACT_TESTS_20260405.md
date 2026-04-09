# Verification: ECO Compare Mode Contract Tests

## Date

2026-04-05

## Test Results

```bash
pytest -q test_eco_compare_mode_router.py test_eco_apply_diagnostics.py \
  test_eco_parallel_flow_hooks.py -k 'compare_mode or compute_changes or impact or bom_diff'
# Result: 11 passed

py_compile (3 test files)
# Result: clean

git diff --check
# Result: clean
```

## Checklist

- [x] impact: compare_mode pass-through locked
- [x] impact: invalid compare_mode → 400 locked
- [x] impact/export: compare_mode pass-through locked
- [x] bom-diff: compare_mode pass-through locked
- [x] bom-diff: invalid compare_mode → 400 locked
- [x] compute-changes: compare_mode pass-through locked
- [x] compute-changes: invalid compare_mode → 400 locked
- [x] compute-changes: None default locked
- [x] No production code changes
