# Lightweight Scheduler Foundation - Development And Verification

Date: 2026-04-21

## 1. Goal

Add the smallest application-level scheduler foundation needed by the Odoo18 gap analysis without introducing a new scheduler dependency or a new persistence table.

The scheduler only decides when periodic work is due and enqueues jobs into the existing `meta_conversion_jobs` queue. Execution remains owned by `JobWorker` and existing task handlers.

## 2. Scope

Implemented:

- `SchedulerService` with static task definitions, due/not-due evaluation, active-job dedupe, and tenant/org scoped dedupe keys.
- `yuantus scheduler` CLI with `--once`, `--force`, `--tenant`, `--org`, and `--poll-interval`.
- Worker handlers for:
  - `eco_approval_escalation`
  - `audit_retention_prune`
- Settings for global enablement, task intervals, priority, max attempts, and scheduler system user.
- Focused tests for scheduler idempotency, scoping, handler delegation, and CLI registration.

## 3. Non-Goals

- No APScheduler dependency.
- No new scheduler database table.
- No outbox implementation.
- No dynamic UI/API for schedule editing.
- No MBOM auto-sync or effectivity pointer switching in this increment.
- No report snapshot scheduler.
- No change to `JobService.poll_next_job()` semantics.

## 4. Runtime Model

The scheduler enqueues due jobs with dedupe keys like:

```text
scheduler:<task-name>:tenant:<tenant-id>:org:<org-id>
```

It skips enqueue when:

- scheduler is disabled and `--force` is not set;
- the individual task is disabled;
- the task interval is `<= 0`;
- a pending/processing job for the same scoped dedupe key already exists;
- the last completed/failed job for the same scoped dedupe key is still within the interval window.

The worker then executes those jobs through the normal job queue path.

## 5. Settings

```text
SCHEDULER_ENABLED=false
SCHEDULER_POLL_INTERVAL_SECONDS=60
SCHEDULER_SYSTEM_USER_ID=1
SCHEDULER_ECO_ESCALATION_ENABLED=true
SCHEDULER_ECO_ESCALATION_INTERVAL_SECONDS=300
SCHEDULER_ECO_ESCALATION_PRIORITY=80
SCHEDULER_ECO_ESCALATION_MAX_ATTEMPTS=1
SCHEDULER_AUDIT_RETENTION_ENABLED=true
SCHEDULER_AUDIT_RETENTION_INTERVAL_SECONDS=3600
SCHEDULER_AUDIT_RETENTION_PRIORITY=95
SCHEDULER_AUDIT_RETENTION_MAX_ATTEMPTS=1
```

Because `SCHEDULER_ENABLED` defaults to false, production does not start periodic enqueueing unless explicitly enabled. Operators can still run a one-shot tick with `--force`.

## 6. Commands

One-shot local tick:

```bash
yuantus scheduler --once --force --tenant tenant-1 --org org-1
```

Long-running scheduler:

```bash
YUANTUS_SCHEDULER_ENABLED=true \
yuantus scheduler --tenant tenant-1 --org org-1
```

Worker still runs separately:

```bash
yuantus worker --tenant tenant-1 --org org-1
```

## 7. Verification

Focused scheduler, job queue, auth, and doc-index tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py \
  src/yuantus/meta_engine/tests/test_jobs_router_auth.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
25 passed, 1 warning
```

The warning is the existing `relationship.models` deprecation warning emitted by `import_all_models()` in test setup.

Coverage:

- global disabled scheduler does not enqueue;
- `--force`/`force=True` can run a one-shot tick;
- scoped tenant/org dedupe key and payload are populated;
- pending/processing active job prevents duplicate enqueue;
- recent completed job skips until interval elapses;
- elapsed interval enqueues a new job;
- disabled task is reported without enqueue;
- default registry remains bounded to two tasks;
- ECO scheduler task delegates to `ECOApprovalService.escalate_overdue_approvals()`;
- audit retention task delegates to `prune_audit_logs()`;
- CLI command and worker handler registration contracts are present.

Syntax and whitespace checks:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/scheduler_service.py \
  src/yuantus/meta_engine/tasks/scheduler_tasks.py \
  src/yuantus/cli.py
git diff --check
```

Result: passed with no output.

## 8. Follow-Up

This foundation is the prerequisite for the next bounded increments:

- ECO activity template scheduling and richer escalation policy.
- MBOM auto-sync enqueue on ECO released event.
- effectivity daily switch/check task.
- report snapshot/aggregation scheduling.
- optional outbox table for event durability.
