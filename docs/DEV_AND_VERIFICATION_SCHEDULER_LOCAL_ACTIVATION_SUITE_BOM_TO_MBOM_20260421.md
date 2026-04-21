# DEV / Verification - Scheduler Local Activation Suite BOM to MBOM Step - 2026-04-21

## 1. Goal

Extend the local scheduler activation suite so it also exercises the existing `bom_to_mbom_sync` consumer.

This closes the local evidence chain from scheduler dry-run through all three currently available activation smokes:

1. audit-retention prune,
2. ECO approval escalation,
3. BOM to MBOM sync.

## 2. Delivered

- `scripts/run_scheduler_local_activation_suite.sh` now invokes `scripts/run_scheduler_bom_to_mbom_activation_smoke.sh` as `04-bom-to-mbom-activation`.
- `scripts/render_scheduler_local_activation_suite.py` now validates and reports BOM to MBOM evidence.
- `scripts/run_scheduler_bom_to_mbom_activation_smoke.sh` cleanup now bulk-deletes generated `MBOMLine` rows before `ManufacturingBOM` rows to keep repeated suite runs warning-free.
- `src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py` covers the new suite step.
- `src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py` covers the new report payload and Markdown section.
- `src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py` pins the cleanup ordering guard.
- Existing suite docs and script index were updated to describe the fourth step.

## 3. Runtime Behavior

The suite remains local-dev only and still refuses non-SQLite DB URLs or SQLite DBs outside `local-dev-env/data`.

The new step delegates to the existing bounded smoke:

```bash
scripts/run_scheduler_bom_to_mbom_activation_smoke.sh
```

Expected artifacts under the suite output directory:

```text
04-bom-to-mbom-activation/validation.json
04-bom-to-mbom-activation/scheduler_tick.json
04-bom-to-mbom-activation/post_worker_summary.json
```

The renderer now requires:

- `bom_to_mbom_sync` was enqueued,
- worker job completed,
- worker result reports `created=1`,
- one `ManufacturingBOM` exists after the run,
- at least two `MBOMLine` rows exist,
- child line preserves EBOM relationship traceability.

## 4. Verification

Focused contract command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Syntax checks:

```bash
bash -n scripts/run_scheduler_local_activation_suite.sh
.venv/bin/python -m py_compile scripts/render_scheduler_local_activation_suite.py
```

Runtime smoke command, if local-dev DB is available:

```bash
bash scripts/run_scheduler_local_activation_suite.sh \
  --output-dir ./tmp/scheduler-local-activation-suite-bom-to-mbom-<timestamp>
```

Observed local verification:

```text
bash -n scripts/run_scheduler_local_activation_suite.sh
bash -n scripts/run_scheduler_bom_to_mbom_activation_smoke.sh
.venv/bin/python -m py_compile scripts/render_scheduler_local_activation_suite.py
27 focused contract tests passed
```

Observed runtime evidence:

```text
tmp/scheduler-local-activation-suite-bom-to-mbom-rerun-20260421-232013/
SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md verdict: PASS
```

Observed BOM to MBOM report fields:

```text
task_type=bom_to_mbom_sync
job_status=completed
created=1
skipped_count=0
mbom_count=1
mbom_line_count=2
traceability_ok=True
```

Additional broad probe:

```text
46 passed, 5 failed in scheduler/MBOM-adjacent sweep
```

The five failures were limited to `test_manufacturing_mbom_router.py` and all returned `401` before reaching MBOM router logic. They are an existing auth-test contract drift outside this PR's scheduler local-suite scope.

## 5. Boundary

- No scheduler runtime default changed.
- No new scheduler task type.
- No schema change.
- No shared-dev 142 mutation or bootstrap.
- No production activation.
- No handler, worker, or scheduler service behavior changes.
