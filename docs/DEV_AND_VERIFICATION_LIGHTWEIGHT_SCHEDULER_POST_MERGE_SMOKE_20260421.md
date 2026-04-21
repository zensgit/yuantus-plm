# Lightweight Scheduler Post-Merge Smoke - Development And Verification

Date: 2026-04-21

## 1. Goal

Close the immediate post-merge gate for PR #313 (`feat: add lightweight scheduler foundation`):

- confirm shared-dev 142 is unchanged when the scheduler remains disabled;
- confirm the local scheduler activation path can enqueue and execute the first low-risk consumer;
- keep shared-dev writes out of this validation round.

## 2. Scope

Executed:

- shared-dev 142 readonly rerun against the official frozen baseline;
- local sqlite activation smoke for `audit_retention_prune`;
- post-smoke documentation and doc-index registration.

Not executed:

- no first-run/bootstrap on shared-dev 142;
- no scheduler activation on shared-dev 142;
- no ECO escalation scheduler activation;
- no source-code changes.

## 3. Shared-Dev 142 No-Op Smoke

Command:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh \
  --mode readonly-rerun \
  -- \
  --output-dir ./tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339
```

Inputs:

- env file: `$HOME/.config/yuantus/p2-shared-dev.env`
- base URL: `http://142.171.239.56:7910`
- tenant/org: `tenant-1 / org-1`
- auth mode: username/password
- baseline label: `shared-dev-142-readonly-20260421`
- baseline policy: `overdue-only-stable`

Result:

```text
precheck summary_http_status=200
summary endpoint=200
items endpoint=200
export json endpoint=200
export csv endpoint=200
anomalies endpoint=200
write smoke=skipped
readonly evaluation=PASS, 20/20 checks
```

Readonly comparison:

| Metric | Baseline | Current | Delta |
|---|---:|---:|---:|
| `pending_count` | 0 | 0 | 0 |
| `overdue_count` | 4 | 4 | 0 |
| `escalated_count` | 1 | 1 | 0 |
| `items_count` | 4 | 4 | 0 |
| `export_json_count` | 4 | 4 | 0 |
| `export_csv_rows` | 4 | 4 | 0 |
| `total_anomalies` | 3 | 3 | 0 |
| `no_candidates` | 0 | 0 | 0 |
| `escalated_unresolved` | 1 | 1 | 0 |
| `overdue_not_escalated` | 2 | 2 | 0 |

Artifacts:

- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339-precheck/OBSERVATION_PRECHECK.md`
- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339/raw-current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339/STABLE_CURRENT_TRANSFORM.md`
- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339/OBSERVATION_DIFF.md`
- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-observation-142-post-merge-pr313-noop-20260421-131339.tar.gz`

Conclusion: PR #313 did not change the shared-dev 142 readonly observation surface when the scheduler remains disabled.

## 4. Local Scheduler Activation Smoke

Environment:

- local sandbox: `local-dev-env`
- database: `sqlite:///local-dev-env/data/yuantus.db`
- tenancy mode: `disabled`
- tenant/org payload: `tenant-1 / org-1`
- retention policy: `YUANTUS_AUDIT_RETENTION_DAYS=1`
- ECO scheduler task: disabled for this smoke
- audit retention scheduler task: enabled

Setup:

```bash
bash local-dev-env/start.sh
```

Seeded audit rows:

```json
{
  "audit_rows_seeded": 3,
  "old_rows_expected_to_delete": 2,
  "new_rows_expected_to_keep": 1,
  "job_rows_cleared": true
}
```

Scheduler tick:

```bash
YUANTUS_DATABASE_URL=sqlite:///local-dev-env/data/yuantus.db \
YUANTUS_TENANCY_MODE=disabled \
YUANTUS_AUDIT_RETENTION_DAYS=1 \
YUANTUS_AUDIT_RETENTION_MAX_ROWS=0 \
YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=false \
YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=true \
.venv/bin/python -m yuantus scheduler --once --force --tenant tenant-1 --org org-1
```

Scheduler result:

```json
{
  "enqueued": [
    {
      "name": "audit_retention_prune",
      "task_type": "audit_retention_prune",
      "action": "enqueued",
      "reason": "due",
      "dedupe_key": "scheduler:audit_retention_prune:tenant:tenant-1:org:org-1"
    }
  ],
  "disabled": [
    {
      "name": "eco_approval_escalation",
      "task_type": "eco_approval_escalation",
      "action": "disabled",
      "reason": "task_disabled"
    }
  ],
  "skipped": []
}
```

Worker execution:

```bash
YUANTUS_DATABASE_URL=sqlite:///local-dev-env/data/yuantus.db \
YUANTUS_TENANCY_MODE=disabled \
YUANTUS_AUDIT_RETENTION_DAYS=1 \
YUANTUS_AUDIT_RETENTION_MAX_ROWS=0 \
YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=false \
YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=true \
.venv/bin/python -m yuantus worker --once --tenant tenant-1 --org org-1
```

Worker result:

```text
Processed one job.
```

Post-worker state:

```json
{
  "job_count": 1,
  "jobs": [
    {
      "task_type": "audit_retention_prune",
      "status": "completed",
      "dedupe_key": "scheduler:audit_retention_prune:tenant:tenant-1:org:org-1",
      "payload_result": {
        "ok": true,
        "task": "audit_retention_prune",
        "deleted": 2,
        "tenant_id": "tenant-1",
        "retention_days": 1,
        "retention_max_rows": 0
      }
    }
  ],
  "audit_count_after": 1,
  "audit_paths_after": [
    "/new-c"
  ]
}
```

Artifacts:

- `tmp/scheduler-activation-local-20260421-131634/audit_seed.json`
- `tmp/scheduler-activation-local-20260421-131634/scheduler_tick.json`
- `tmp/scheduler-activation-local-20260421-131634/worker_once.txt`
- `tmp/scheduler-activation-local-20260421-131634/post_worker_summary.json`

Conclusion: the scheduler can enqueue the audit-retention consumer, the existing worker can execute it, and the handler prunes old audit rows while preserving new rows.

## 5. Boundary Notes

- Shared-dev 142 was only read through the existing readonly observation path.
- The scheduler remains default-off in settings.
- The local activation smoke used `--force` and explicit task-level env toggles.
- `eco_approval_escalation` was intentionally disabled in the local activation smoke to keep this first consumer validation low-risk.
- The `cadquery not installed` message printed during worker startup is unrelated to this smoke; it comes from CAD task imports and did not block job execution.

## 6. Follow-Up

Recommended next bounded increment:

1. Audit retention activation runbook and guardrails.
2. ECO escalation scheduler activation as a separate PR with before/after dashboard and audit-anomaly reconciliation.
3. Only after those are stable, use scheduler for MBOM/effectivity/reporting work.
