# Scheduler Compose Service

## Goal

Expose the lightweight scheduler as an opt-in Docker Compose service without changing the default local/shared-dev startup path.

## Change

- Added `scheduler` to `docker-compose.yml`.
- The service uses `profiles: ["scheduler"]`, so plain `docker compose up api worker` does not start it.
- The service reuses `Dockerfile.worker` and runs `yuantus scheduler`.
- `YUANTUS_SCHEDULER_ENABLED=false` remains the default, so selecting the profile still does not enqueue periodic work unless explicitly enabled.
- The service waits for `api: service_healthy`, which keeps migrations owned by the API startup path.
- The service does not run first-run bootstrap and does not seed/reset data.

## Operator Commands

Render and inspect the service without starting it:

```bash
docker compose --profile scheduler config
```

Start the scheduler container in disabled mode:

```bash
docker compose --profile scheduler up -d scheduler
```

Enable the scheduler loop explicitly:

```bash
YUANTUS_SCHEDULER_ENABLED=true \
docker compose --profile scheduler up -d scheduler
```

Tune task switches explicitly:

```bash
YUANTUS_SCHEDULER_ENABLED=true \
YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=true \
YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=true \
docker compose --profile scheduler up -d scheduler
```

## Safety Boundaries

- Default compose behavior is unchanged.
- The scheduler service does not use `--force`.
- The scheduler service has no `restart` policy, avoiding a restart loop when the profile is selected but `YUANTUS_SCHEDULER_ENABLED=false`.
- Scheduler activation remains an explicit environment decision.
- Shared-dev first-run/bootstrap remains separate from this service.

## Verification

Focused contract tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_compose_service_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_compose_worker_dedup_vision_url.py \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Compose render check:

```bash
docker compose --profile scheduler config
```

## Result

Local verification passed.

- Focused tests: `24 passed, 1 warning` (`yuantus.meta_engine.relationship.models` deprecation warning already exists in scheduler tests)
- Compose render: `docker compose --profile scheduler config` succeeded
- Default services check: `docker compose config --services` excludes `scheduler`
- Profile services check: `docker compose --profile scheduler config --services` includes `scheduler`
