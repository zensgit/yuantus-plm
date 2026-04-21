# Scheduler Audit Retention Activation Runbook - Development And Verification

Date: 2026-04-21

## 1. Goal

Turn the first scheduler consumer into an operator-safe, repeatable activation smoke without enabling scheduler on shared-dev 142 by default.

This increment intentionally focuses on `audit_retention_prune` because it is lower risk than ECO escalation:

- it only prunes audit rows according to existing retention settings;
- it does not mutate ECO stage, approval state, or dashboard anomalies;
- it exercises the same scheduler enqueue and worker consume path that later ECO escalation will use.

## 2. Scope

Implemented:

- `scripts/run_scheduler_audit_retention_activation_smoke.sh`
- contract tests for script syntax, help text, guardrails, and doc-index registration
- this development and verification record
- `DELIVERY_DOC_INDEX.md` registration
- `DELIVERY_SCRIPTS_INDEX_20260202.md` registration
- `.github/workflows/ci.yml` contracts-step registration for the new contract test

Not implemented:

- no shared-dev 142 scheduler activation
- no production scheduler activation
- no ECO escalation scheduler activation
- no source-code change to scheduler, worker, or audit-retention handler behavior

## 3. Guardrails

The activation smoke script is local-only by design.

Hard guards:

- refuses non-SQLite DB URLs;
- refuses DB paths outside `./local-dev-env/data/`;
- requires the target local DB file to already exist;
- clears only `audit_logs` and `meta_conversion_jobs` in that local DB;
- disables `eco_approval_escalation` for the smoke;
- enables only `audit_retention_prune` for the scheduler tick.

This means shared-dev 142 remains default-off for scheduler activation. Any shared-dev scheduler enablement must be a separate change with explicit approval and its own evidence pack.

## 4. Operator Command

Prepare the local DB:

```bash
bash local-dev-env/start.sh
```

Run the activation smoke:

```bash
bash scripts/run_scheduler_audit_retention_activation_smoke.sh
```

Optional explicit output directory:

```bash
bash scripts/run_scheduler_audit_retention_activation_smoke.sh \
  --output-dir ./tmp/scheduler-audit-retention-activation-$(date +%Y%m%d-%H%M%S)
```

The script writes:

- `audit_seed.json`
- `scheduler_tick.json`
- `worker_once.txt`
- `post_worker_summary.json`
- `validation.json`
- `README.txt`

## 5. Expected Result

The smoke seeds three local audit rows:

- two old rows, expected to be deleted;
- one new row, expected to be retained.

Expected scheduler result:

```text
audit_retention_prune: enqueued
eco_approval_escalation: disabled
```

Expected worker result:

```text
Processed one job.
```

Expected final state:

```text
job_count=1
job.status=completed
job.task_type=audit_retention_prune
payload_result.deleted=2
audit_count_after=1
audit_paths_after=["/scheduler-smoke/new-c"]
validation.ok=true
```

## 6. Verification

Local script execution:

```bash
bash scripts/run_scheduler_audit_retention_activation_smoke.sh \
  --output-dir ./tmp/scheduler-audit-retention-activation-20260421-133559
```

Result:

```text
Done:
  ./tmp/scheduler-audit-retention-activation-20260421-133559/audit_seed.json
  ./tmp/scheduler-audit-retention-activation-20260421-133559/scheduler_tick.json
  ./tmp/scheduler-audit-retention-activation-20260421-133559/worker_once.txt
  ./tmp/scheduler-audit-retention-activation-20260421-133559/post_worker_summary.json
  ./tmp/scheduler-audit-retention-activation-20260421-133559/validation.json
```

Validation summary:

```json
{
  "ok": true,
  "errors": []
}
```

Focused tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_audit_retention_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
35 passed, 1 warning
```

Syntax and whitespace:

```bash
bash -n scripts/run_scheduler_audit_retention_activation_smoke.sh
git diff --check
```

Result: passed.

## 7. Shared-Dev 142 Boundary

No shared-dev write was performed in this increment.

The prior post-merge no-op evidence remains the shared-dev gate:

- `docs/DEV_AND_VERIFICATION_LIGHTWEIGHT_SCHEDULER_POST_MERGE_SMOKE_20260421.md`
- readonly evaluation: `PASS, 20/20 checks`
- scheduler activation on 142: not performed

## 8. Follow-Up

Recommended next bounded increment:

1. ECO escalation scheduler activation as a separate PR.
2. Before/after dashboard and audit-anomaly reconciliation for ECO escalation.
3. Only after ECO activation is stable, use scheduler for MBOM, effectivity, and reporting work.
