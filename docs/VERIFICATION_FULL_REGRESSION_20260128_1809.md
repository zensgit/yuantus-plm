# Verification - Full Regression Run

Date: 2026-01-28

## Command

```bash
scripts/run_full_regression.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Result Summary

- PASS: 44
- FAIL: 0
- SKIP: 8

Skipped:
- S8 (Ops Monitoring) - `RUN_OPS_S8=0`
- S5-A (CADGF Preview Online) - `RUN_CADGF_PREVIEW_ONLINE=0`
- UI Product Detail / Summary / Where-Used / BOM / Docs Approval / Docs ECO Summary - `RUN_UI_AGG=0`

## Output (Tail)

```
PASS: 44  FAIL: 0  SKIP: 8

ALL TESTS PASSED
```
