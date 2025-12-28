# Day 65 Report

Date: 2025-12-27

## Scope
- Recreate api/worker with platform admin override and run full regression via run_full_regression.sh.

## Work Completed
- Recreated docker compose services for api/worker.
- Executed full regression script with all optional CAD/extractor/provisioning checks.

## Verification

Command:
```
scripts/run_full_regression.sh http://127.0.0.1:7910 tenant-1 org-1 | tee /tmp/verify_all_full_open3.log
```

Results:
- PASS: 42
- FAIL: 0
- SKIP: 0

Artifacts:
- /tmp/verify_all_full_open3.log
- docs/VERIFICATION_RESULTS.md (Run ALL-62)
