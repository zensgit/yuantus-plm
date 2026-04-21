# Scheduler Dry-Run Preflight - Development And Verification

Date: 2026-04-21

## 1. Goal

Add a non-mutating scheduler preflight path before any shared-dev or production scheduler activation.

The new path lets operators run the same scheduler due/skip/disabled logic and see what would enqueue, without creating rows in `meta_conversion_jobs`.

## 2. Change Summary

Changed:

- `src/yuantus/meta_engine/services/scheduler_service.py`
- `src/yuantus/cli.py`
- `src/yuantus/meta_engine/tests/test_scheduler_service.py`
- `docs/DELIVERY_DOC_INDEX.md`

Behavior:

- `SchedulerService.run_once(dry_run=True)` reports due tasks as `would_enqueue`.
- dry-run never calls `JobService.create_job()`.
- existing skip and disabled decisions are preserved.
- `yuantus scheduler --dry-run` emits a new JSON field: `would_enqueue`.
- `yuantus scheduler --dry-run --force` can safely evaluate disabled global scheduler environments without writing jobs.

## 3. CLI Contract

Example:

```bash
.venv/bin/python -m yuantus scheduler \
  --once \
  --dry-run \
  --force \
  --tenant tenant-1 \
  --org org-1
```

Expected output shape:

```json
{
  "disabled": [],
  "enqueued": [],
  "skipped": [],
  "would_enqueue": [
    {
      "action": "would_enqueue",
      "dedupe_key": "scheduler:<task>:tenant:tenant-1:org:org-1",
      "job_id": null,
      "reason": "dry_run_due",
      "task_type": "<task>"
    }
  ]
}
```

If an active job already exists, dry-run still reports `skipped: active_job_exists`. If a task is disabled, dry-run still reports `disabled: task_disabled`.

## 4. Safety Boundary

shared-dev 142 remains default-off.

This increment does not:

- enable scheduler on 142;
- enable scheduler in production;
- add a long-running scheduler deployment unit;
- change ECO escalation or audit-retention business logic;
- change worker execution behavior.

The intended next operational sequence is:

1. run readonly P2 observation on 142;
2. run scheduler dry-run preflight against the intended environment;
3. review `would_enqueue` output;
4. only then decide whether a separate scheduler enablement PR is justified.

## 5. Verification

Focused scheduler tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_scheduler_audit_retention_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_eco_escalation_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Key assertions:

- dry-run due task returns `would_enqueue_count == 1`;
- dry-run does not create `ConversionJob` rows;
- dry-run preserves `active_job_exists` skip semantics;
- CLI source wires `--dry-run` into `SchedulerService.run_once(force=force, dry_run=dry_run)`;
- CLI JSON includes `would_enqueue`.

Local CLI smoke:

```bash
PYTHONPATH=src \
YUANTUS_DATABASE_URL=sqlite:///$PWD/local-dev-env/data/yuantus.db \
YUANTUS_TENANCY_MODE=disabled \
.venv/bin/python -m yuantus scheduler \
  --once --dry-run --force --tenant tenant-1 --org org-1
```

Observed:

```text
before job count: 1
after job count:  1
would_enqueue: eco_approval_escalation, audit_retention_prune
```

## 6. Acceptance

| Criterion | Status |
| --- | --- |
| Due tasks can be evaluated without queue writes | Pass |
| Existing disabled/skipped semantics remain intact | Pass |
| CLI exposes `--dry-run` | Pass |
| CLI output has `would_enqueue` | Pass |
| Shared-dev 142 remains default-off | Pass |
