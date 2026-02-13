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

## Follow-Up: MT Overlay Alignment + Suite Stabilization

### Why

When local `.env` sets `YUANTUS_TENANCY_MODE=db-per-tenant-org`, `START_DEDUP_STACK=1` was previously starting only `docker-compose.yml` (no multi-tenant overlay), which results in a misconfigured runtime:

- API runs `TENANCY_MODE=db-per-tenant-org` but with an empty `DATABASE_URL_TEMPLATE` in docker-compose, so tenant/org isolation does not work (tables are not tenant-scoped by columns; isolation must be DB-level).
- Host-side verification scripts/DB validations may compute and use a `DB_URL_TEMPLATE` anyway, causing DB mismatch (API reads `yuantus`, scripts write/read `yuantus_mt_pg__*`).

### Changes (2026-02-13)

- `scripts/verify_all.sh`
  - When `START_DEDUP_STACK=1` and `YUANTUS_TENANCY_MODE=db-per-tenant-org`, automatically includes `docker-compose.mt.yml`.
  - In MT overlay mode, starts `api/worker` **without** `--no-deps` so `mt-bootstrap` can run.
  - Selects the correct identity DB name in MT mode (`yuantus_identity_mt_pg`) vs single (`yuantus_identity`).
  - Exports `YUANTUS_IDENTITY_DATABASE_URL` earlier so CLI fallbacks (e.g. seeding admin if login fails) stay consistent with the API.
  - Keeps identity DB env intact even when `tenancy_mode=single` (identity split is orthogonal to tenancy mode).
- `scripts/verify_bom_effectivity.sh`
  - Seeds a unique viewer per run (`viewer-$TS`) to avoid `auth_users` primary-key collisions.
  - Keeps Permission ACE `identity_id` set to the *role* `viewer` (permission checks match against roles + user id, not username).
- `scripts/verify_cad_dedup_vision_s3.sh`
  - Generates a seed-dependent block-pattern PNG pair (baseline/query differ by a single pixel) to reduce cross-run false matches and make the baseline match deterministic.
- `scripts/verify_cad_filename_parse.sh`, `scripts/verify_cad_attribute_normalization.sh`
  - Force `YUANTUS_STORAGE_TYPE=local` so local/offline tests do not inherit `s3` from outer suites.

### Verification (Local)

Command:

```bash
RUN_DEDUP=1 START_DEDUP_STACK=1 USE_DOCKER_WORKER=1 bash scripts/verify_all.sh
```

Result:

- `PASS: 42  FAIL: 0  SKIP: 19`
- Evidence log: `tmp/verify_all_20260213-143456.log`

Note (MT schema drift):

- `docker-compose.mt.yml` uses `SCHEMA_MODE=create_all`, which will not migrate/alter existing tenant DB schemas. If you previously ran MT mode and tenant DBs are stale, reset them (destructive):

```bash
docker stop yuantus-api-1 yuantus-worker-1
DBS=(yuantus_identity_mt_pg yuantus_mt_pg__tenant-1__org-1 yuantus_mt_pg__tenant-1__org-2 yuantus_mt_pg__tenant-2__org-1 yuantus_mt_pg__tenant-2__org-2)
for db in "${DBS[@]}"; do docker exec -i yuantus-postgres-1 dropdb -U yuantus --if-exists --force "$db" || true; done
for db in "${DBS[@]}"; do docker exec -i yuantus-postgres-1 createdb -U yuantus "$db"; done
docker compose -f docker-compose.yml -f docker-compose.mt.yml --profile dedup up -d api worker
```
