# P1 CAD PR Broader Regression

Date: 2026-04-15

## Goal

Add a broader post-PR regression snapshot on top of the already recorded focused
validation for PR `#201`.

This round does not expand product scope. It increases reviewer confidence by
covering more cross-cutting CAD queue/checkin/read-surface/viewer contracts.

PR:

- `#201` `Migrate CAD conversion runtime to canonical queue and close out P1 CAD work`

## Regression batches

### Batch A: checkin runtime chain

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_checkin_manager.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_transaction.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py
```

Observed:

- `21 passed, 1 warning`

### Batch B: file conversion routers and legacy audit

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_queue_shim.py \
  src/yuantus/meta_engine/tests/test_audit_legacy_cad_conversion_jobs_script.py
```

Observed:

- `24 passed, 5 warnings`

### Batch C: viewer and queue boundary contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_viewer_readiness.py \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_preview_min_size.py
```

Observed:

- `43 passed, 1 warning`

## Combined result

- `88 passed`
- warnings remained limited to:
  - environment-level `urllib3/LibreSSL`
  - existing Pydantic deprecation warnings in mocked router tests

## Why this matters

Compared with the earlier focused `45 passed` snapshot, this broader round adds
confidence across:

- checkin job enqueue + binding
- status/read-surface routes
- file upload preview queue
- legacy audit behavior
- viewer readiness
- queue transaction boundary expectations

## Limits

- This still is not a full-repository regression
- It is a broader PR-targeted regression around the CAD queue migration surface

## Claude Code CLI

This round did call `Claude Code CLI` only as a short read-only helper for test
surface selection. Test execution and result recording remained local.
