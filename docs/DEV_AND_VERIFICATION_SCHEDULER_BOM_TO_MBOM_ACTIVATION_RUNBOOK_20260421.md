# Scheduler BOM To MBOM Activation Runbook - Development And Verification

Date: 2026-04-21

## 1. Goal

Activate the scheduler `bom_to_mbom_sync` consumer in a bounded, local-dev-only way:

- enqueue `bom_to_mbom_sync` through `yuantus scheduler`;
- execute it through the existing `yuantus worker`;
- prove the path `scheduler -> meta_conversion_jobs -> worker` creates one `ManufacturingBOM`;
- prove generated `MBOMLine` rows preserve EBOM relationship traceability;
- keep shared-dev 142 and production scheduler activation out of scope.

This follows the audit-retention and ECO escalation activation smokes. The previous handler PR proved the handler contract; this runbook proves it can be activated through the real scheduler and worker path.

## 2. Scope

Changed:

- `scripts/run_scheduler_bom_to_mbom_activation_smoke.sh`
- `src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

Not changed:

- no scheduler service behavior change;
- no worker behavior change;
- no `bom_to_mbom_sync` handler behavior change;
- no MBOM schema or migration;
- no local activation suite expansion;
- no shared-dev 142 scheduler activation;
- no production scheduler activation.

## 3. Safety Model

The script is intentionally destructive only for fixed smoke fixtures inside local dev:

```bash
scripts/run_scheduler_bom_to_mbom_activation_smoke.sh
```

Guardrails:

- refuses non-SQLite database URLs;
- refuses DB paths outside `./local-dev-env/data/`;
- requires the DB file to already exist;
- clears only fixed BOM->MBOM smoke items, generated MBOM rows for that source item, and `meta_conversion_jobs`;
- enables only `YUANTUS_SCHEDULER_BOM_TO_MBOM_ENABLED=true`;
- disables `YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=false`;
- disables `YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=false`;
- uses `yuantus scheduler --once --force` instead of enabling the long-running scheduler.

shared-dev 142 remains default-off. Any shared-dev scheduler activation must be a separate explicit decision with its own evidence pack.

## 4. Seeded Scenario

The script seeds a minimal Released EBOM:

| Record | ID | State | Purpose |
| --- | --- | --- | --- |
| root Part | `scheduler-smoke-ebom-root` | `Released` | source item allowlisted in scheduler payload |
| child Part | `scheduler-smoke-ebom-child` | `Released` | child material line |
| Part BOM relationship | `scheduler-smoke-ebom-rel` | `Active` | EBOM edge with `quantity=2`, `uom=EA`, `find_num=10` |

Expected transition:

| Artifact | Before | After |
| --- | ---: | ---: |
| enqueued scheduler jobs | 0 | 1 `bom_to_mbom_sync` |
| completed worker jobs | 0 | 1 |
| `ManufacturingBOM` rows for root | 0 | 1 |
| `MBOMLine` rows for created MBOM | 0 | at least 2 |
| root line | absent | present |
| child line | absent | present with EBOM relationship traceability |

## 5. Evidence Artifacts

Example run:

```bash
bash scripts/run_scheduler_bom_to_mbom_activation_smoke.sh \
  --output-dir ./tmp/scheduler-bom-to-mbom-activation-20260421-180000
```

Artifacts:

- `bom_seed.json`
- `before_summary.json`
- `before_snapshot.json`
- `scheduler_tick.json`
- `worker_once.txt`
- `after_summary.json`
- `after_snapshot.json`
- `post_worker_summary.json`
- `validation.json`
- `README.txt`

Expected validation:

```json
{
  "errors": [],
  "ok": true
}
```

Expected scheduler tick:

- enqueued: `bom_to_mbom_sync`;
- disabled: `eco_approval_escalation`;
- disabled: `audit_retention_prune`;
- dedupe key includes `scheduler:bom_to_mbom_sync:tenant:tenant-1:org:org-1`.

Expected worker result:

- job status: `completed`;
- worker id: `scheduler-bom-to-mbom-smoke`;
- result task: `bom_to_mbom_sync`;
- result `created`: `1`;
- result `errors`: `[]`.

Observed local run:

```text
OUTPUT_DIR=./tmp/scheduler-bom-to-mbom-activation-20260421-codex
```

Observed validation:

```json
{
  "errors": [],
  "ok": true
}
```

Observed result:

| Field | Value |
| --- | --- |
| enqueued task | `bom_to_mbom_sync` |
| disabled tasks | `eco_approval_escalation`, `audit_retention_prune` |
| job status | `completed` |
| worker id | `scheduler-bom-to-mbom-smoke` |
| worker result `created` | `1` |
| worker result `errors` | `[]` |
| created `ManufacturingBOM` count | `1` |
| created `MBOMLine` count | `2` |
| plant code | `PLANT-SMOKE` |
| child traceability | `ebom_relationship_id=scheduler-smoke-ebom-rel` |

## 6. Verification Commands

Focused verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_service.py \
  src/yuantus/meta_engine/tests/test_scheduler_compose_service_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Observed result:

```text
55 passed, 1 warning
```

The warning is the existing relationship model deprecation emitted by bootstrap import.

Shell checks:

```bash
bash -n scripts/run_scheduler_bom_to_mbom_activation_smoke.sh
scripts/run_scheduler_bom_to_mbom_activation_smoke.sh --help
git diff --check
```

Observed result:

```text
pass
```

Activation smoke:

```bash
bash scripts/run_scheduler_bom_to_mbom_activation_smoke.sh \
  --output-dir ./tmp/scheduler-bom-to-mbom-activation-$(date +%Y%m%d-%H%M%S)
```

## 7. Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Script refuses non-local DB targets | Pass |
| Scheduler enqueues exactly one `bom_to_mbom_sync` job | Pass |
| `eco_approval_escalation` is disabled during this smoke | Pass |
| `audit_retention_prune` is disabled during this smoke | Pass |
| Worker completes the job | Pass |
| Worker result reports `created=1` and no errors | Pass |
| One `ManufacturingBOM` is created for the source Part | Pass |
| Generated `MBOMLine` rows include root and child items | Pass |
| Child `MBOMLine` keeps `ebom_relationship_id` traceability | Pass |
| Script and doc are indexed | Pass |

## 8. Boundary

This is an activation smoke/runbook increment, not a scheduler default-enable change. It deliberately does not add the script to the local activation suite yet, because BOM->MBOM seed data is more invasive than audit retention or ECO escalation fixtures.

Next bounded increment options:

- add a no-op 142 readback check that proves the task remains default-off;
- promote the smoke into the local activation suite after one more stable run;
- continue with the next `§一.5` MBOM scheduling capability.
