# Dev Log (2026-02-13): START_DEDUP_STACK + USE_DOCKER_WORKER

## Goal

- Add `START_DEDUP_STACK=1` to `scripts/verify_all.sh` to one-click start the Dedup stack (`docker compose --profile dedup up -d ...`) before running the suite.
- Extend `USE_DOCKER_WORKER=1` mode across CAD verification scripts so they can wait for a running docker-compose `worker` (instead of running local `yuantus worker --once`).

## What Changed

### 1) `START_DEDUP_STACK=1` for `verify_all.sh`

- `scripts/verify_all.sh`
  - New flag: `START_DEDUP_STACK` (truthy: `1/true/yes/on`).
  - When enabled, starts the dedup compose stack via:
    - `docker compose -f docker-compose.yml --profile dedup up -d postgres minio`
    - `docker compose -f docker-compose.yml --profile dedup up -d --build --no-deps api worker`
    - `docker compose -f docker-compose.yml --profile dedup up -d dedup-vision`
  - API health check now retries (default: 60 attempts with 2s sleep) when `START_DEDUP_STACK=1` to avoid failing while the stack is still warming up.
  - DB port probing now uses `docker compose -f "${REPO_ROOT}/docker-compose.yml" port ...` (no dependency on current working directory).

### 2) `USE_DOCKER_WORKER=1` in CAD verification scripts

When `USE_DOCKER_WORKER=1`, scripts do not run local `yuantus worker --once`. They poll job status until terminal (or timeout), expecting an external worker (for example docker-compose `worker`) to process jobs.

- `scripts/verify_cad_pipeline_s3.sh`
  - Skip local worker in docker mode; wait for preview/geometry jobs to reach a terminal status (best-effort, warns on timeout; script stays lenient/partial-success as before).
- `scripts/verify_cad_sync.sh`
  - In docker mode: wait for `cad_extract` job to complete; skip local worker and skip direct python “processor fallback”.
- `scripts/verify_cad_connectors_real_2d.sh`
  - In docker mode: wait for `cad_extract` job completion; skip local worker and skip direct python fallback.
- `scripts/verify_cad_ml_queue_smoke.sh`
  - In docker mode: skip local worker; keep polling job statuses until queue drains.
  - Default `CAD_ML_QUEUE_WORKER_RUNS` is bumped to `60` (only when docker mode is enabled and the env var is not explicitly set) to accommodate compose worker `--poll-interval 5`.
- `scripts/verify_cad_missing_source.sh`
  - In docker mode: skip local worker; wait for the preview job to fail (missing source) and then assert `failed`, `attempt_count=1`, and error text.

## How To Run

### One-click Dedup verification via `verify_all.sh`

```bash
RUN_DEDUP=1 START_DEDUP_STACK=1 USE_DOCKER_WORKER=1 bash scripts/verify_all.sh
```

Notes:

- `RUN_DEDUP=1` enables the dedup verification suites (dedup vision + relationship).
- `START_DEDUP_STACK=1` starts the required docker compose services (including `dedup-vision`).
- `USE_DOCKER_WORKER=1` makes CAD scripts wait for the docker-compose `worker` container instead of running local one-shot workers.

### Run an individual CAD verification script (docker worker mode)

```bash
USE_DOCKER_WORKER=1 bash scripts/verify_cad_sync.sh
```

## Validation Performed (Local)

- Shell syntax checks:
  - `bash -n scripts/verify_all.sh scripts/verify_cad_pipeline_s3.sh scripts/verify_cad_sync.sh scripts/verify_cad_connectors_real_2d.sh scripts/verify_cad_ml_queue_smoke.sh scripts/verify_cad_missing_source.sh`
- CI contract test for shell scripts:
  - `./.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
  - Result: `3 passed`

