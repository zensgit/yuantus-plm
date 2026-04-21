# DEV / Verification - Scheduler Jobs API Readback Smoke - 2026-04-21

## 1. Goal

Close the remaining local scheduler evidence gap after dry-run and activation smoke:

`scheduler --once` -> `worker --once` -> `GET /api/v1/jobs/{job_id}`.

The new helper proves the completed scheduler job is visible through the authenticated Jobs API, not only through direct database inspection.

## 2. Delivered

- `scripts/run_scheduler_jobs_api_readback_smoke.sh`
- `src/yuantus/meta_engine/tests/test_scheduler_jobs_api_readback_smoke_contracts.py`
- CI contracts wiring in `.github/workflows/ci.yml`
- Script syntax wiring in `test_ci_shell_scripts_syntax.py`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Script Behavior

The helper is local-dev only.

1. Runs `scripts/run_scheduler_audit_retention_activation_smoke.sh`.
2. Extracts the scheduler-created `audit_retention_prune` job id from `scheduler_tick.json`.
3. Logs into `BASE_URL/api/v1/auth/login` when `--token` is absent.
4. Calls `GET /api/v1/jobs/{job_id}`.
5. Writes:
   - `activation/scheduler_tick.json`
   - `activation/worker_once.txt`
   - `activation/validation.json`
   - `job_readback.json`
   - `validation.json`
   - `README.txt`

## 4. Safety Boundary

- Refuses non-SQLite DB URLs.
- Refuses SQLite DBs outside `local-dev-env/data`.
- Not for shared-dev or production.
- The activation step is intentionally destructive inside the local-dev SQLite database.

## 5. Validation Contract

`validation.json` passes only when:

- activation smoke passed,
- Jobs API returns the expected `job_id`,
- `task_type == "audit_retention_prune"`,
- `status == "completed"`,
- `worker_id` and `completed_at` are present,
- `payload.result.task == "audit_retention_prune"`,
- `payload.result.deleted == 2`.

## 6. Verification

Focused contract command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_jobs_api_readback_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Runtime smoke command:

```bash
bash scripts/run_scheduler_jobs_api_readback_smoke.sh \
  --base-url http://127.0.0.1:7910 \
  --output-dir ./tmp/scheduler-jobs-api-readback-<timestamp>
```

Prerequisite: `local-dev-env/start.sh` must be running against the same `local-dev-env/data/yuantus.db`.

## 7. Non-Goals

- No scheduler runtime behavior changes.
- No shared-dev 142 scheduler activation.
- No production scheduler enablement.
- No new task handler.

