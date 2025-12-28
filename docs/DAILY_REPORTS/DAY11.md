# Day 11 - CAD Pipeline Missing Source Stability

## Scope
- Prevent retry storms when CAD source files are missing.

## Changes
- Introduced `JobFatalError` and non-retryable failure path in `JobService`/`JobWorker`.
- Added missing-source guards in CAD pipeline tasks and CAD attribute extraction.
- Added `scripts/verify_cad_missing_source.sh` for regression verification.

## Verification

Command:

```bash
DB_URL='sqlite:////tmp/yuantus_missing_source.db' \
IDENTITY_DB_URL='sqlite:////tmp/yuantus_missing_source_identity.db' \
LOCAL_STORAGE_PATH='/tmp/yuantus_missing_source_storage' \
  bash scripts/verify_cad_missing_source.sh http://127.0.0.1:7912 tenant-1 org-1
```

Result:

```text
Job failed without retries
ALL CHECKS PASSED
```

## Additional Regression

Command:

```bash
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_cad_pipeline_s3.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```
