# Scheduler ECO Escalation Activation Runbook - Development And Verification

Date: 2026-04-21

## 1. Goal

Activate the second lightweight scheduler consumer in a bounded, local-dev-only way:

- enqueue `eco_approval_escalation` through `yuantus scheduler`;
- execute it through the existing `yuantus worker`;
- prove the dashboard and anomaly read surfaces reflect the state transition;
- keep shared-dev 142 and production scheduler activation out of scope.

This follows the previous audit-retention activation smoke and uses the same scheduler -> meta_conversion_jobs -> worker path.

## 2. Scope

Changed:

- `scripts/run_scheduler_eco_escalation_activation_smoke.sh`
- `src/yuantus/meta_engine/tests/test_scheduler_eco_escalation_activation_smoke_contracts.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

Not changed:

- no scheduler service behavior change;
- no worker behavior change;
- no ECO escalation business logic change;
- no shared-dev 142 scheduler activation;
- no production scheduler activation.

## 3. Safety Model

The script is intentionally destructive only inside local dev:

```bash
scripts/run_scheduler_eco_escalation_activation_smoke.sh
```

Guardrails:

- refuses non-SQLite database URLs;
- refuses DB paths outside `./local-dev-env/data/`;
- clears local ECO smoke data and `meta_conversion_jobs`;
- enables only `YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=true`;
- disables `YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=false`;
- uses `--once --force` instead of enabling the long-running scheduler.

shared-dev 142 remains default-off. Any shared-dev scheduler activation must be a separate explicit decision with its own evidence pack.

## 4. Seeded Scenario

The script seeds one review stage and three ECOs:

| ECO | Deadline | Initial approval | Purpose |
| --- | --- | --- | --- |
| `scheduler-smoke-pending` | future | admin pending | stable pending row |
| `scheduler-smoke-overdue-admin` | past | admin pending, non-admin role | bridge repair/idempotent guard |
| `scheduler-smoke-overdue-ops` | past | ops pending | real escalation target |

Expected transition:

| Metric | Before | After | Meaning |
| --- | ---: | ---: | --- |
| `pending_count` | 1 | 1 | future pending unchanged |
| `overdue_count` | 2 | 3 | admin escalation creates one extra pending approval row |
| `escalated_count` | 0 | 1 | new admin escalation visible |
| `overdue_not_escalated` | 2 | 1 | one overdue ECO moved out of not-escalated set |
| `escalated_unresolved` | 0 | 1 | escalated admin approval is still pending |
| `ApprovalRequest` bridges | 0 | 2 | one bridge repair plus one new escalation bridge |

## 5. Evidence Artifacts

Example run:

```bash
bash scripts/run_scheduler_eco_escalation_activation_smoke.sh \
  --output-dir ./tmp/scheduler-eco-escalation-activation-20260421-135549
```

Artifacts:

- `eco_seed.json`
- `before_summary.json`
- `before_items.json`
- `before_anomalies.json`
- `scheduler_tick.json`
- `worker_once.txt`
- `after_summary.json`
- `after_items.json`
- `after_anomalies.json`
- `post_worker_summary.json`
- `validation.json`
- `README.txt`

Observed validation:

```json
{
  "errors": [],
  "ok": true
}
```

Observed scheduler tick:

- enqueued: `eco_approval_escalation`
- disabled: `audit_retention_prune`
- dedupe key: `scheduler:eco_approval_escalation:tenant:tenant-1:org:org-1`

Observed worker result:

- job status: `completed`
- worker id: `scheduler-eco-escalation-smoke`
- result task: `eco_approval_escalation`
- result `escalated`: `1`

## 6. Verification Commands

Focused verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_eco_escalation_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_audit_retention_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_eco_approval_escalation.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed result:

```text
49 passed, 1 warning
```

Shell checks:

```bash
bash -n scripts/run_scheduler_eco_escalation_activation_smoke.sh
scripts/run_scheduler_eco_escalation_activation_smoke.sh --help
git diff --check
```

Activation smoke:

```bash
bash scripts/run_scheduler_eco_escalation_activation_smoke.sh \
  --output-dir ./tmp/scheduler-eco-escalation-activation-$(date +%Y%m%d-%H%M%S)
```

## 7. Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Script refuses non-local DB targets | Pass |
| Scheduler enqueues exactly one `eco_approval_escalation` job | Pass |
| `audit_retention_prune` is disabled during this smoke | Pass |
| Worker completes the job | Pass |
| Worker result reports `escalated=1` | Pass |
| Dashboard summary changes `overdue_count 2 -> 3` and `escalated_count 0 -> 1` | Pass |
| Audit anomalies change `overdue_not_escalated 2 -> 1` and `escalated_unresolved 0 -> 1` | Pass |
| Generic approval bridges are present | Pass |
| Script and doc are indexed | Pass |
| CI contracts list includes the new contract test | Pass |

## 8. Boundary

This is an activation smoke/runbook increment, not a scheduler default-enable change. The shared-dev 142 path remains read-only/default-off until there is a separate approval to run scheduler consumers there.

Next bounded increment: decide whether to promote a shared-dev read-only verification for scheduler evidence, or continue to a separate operational runbook for long-running scheduler deployment.
