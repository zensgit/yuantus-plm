# DEV / Verification - Scheduler Local Activation Suite Report - 2026-04-21

## 1. Goal

Turn the scheduler local activation suite artifact directory into a reviewable report.

The renderer summarizes:

- dry-run preflight,
- audit-retention activation,
- ECO escalation activation,
- BOM to MBOM activation,
- per-step validation status,
- expected state transitions.

## 2. Delivered

- `scripts/render_scheduler_local_activation_suite.py`
- `scripts/run_scheduler_local_activation_suite.sh` now invokes the renderer automatically
- `src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py`
- `src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py` updated to require report artifacts
- `.github/workflows/ci.yml` contract wiring
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Output

The suite now writes:

- `SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md`
- `scheduler_local_activation_suite_report.json`

The report verdict is `PASS` only when all checks are true:

- suite validation is green,
- dry-run validation is green,
- dry-run does not change `meta_conversion_jobs`,
- audit-retention worker job completes,
- audit-retention deletes two old audit rows,
- ECO escalation worker job completes,
- ECO escalation returns `escalated=1`,
- `overdue_not_escalated` changes `2 -> 1`,
- `escalated_unresolved` changes `0 -> 1`,
- BOM to MBOM worker job completes,
- BOM to MBOM creates one `ManufacturingBOM`,
- BOM to MBOM creates at least two `MBOMLine` rows and preserves EBOM relationship traceability.

## 4. Runtime Verification

Command:

```bash
bash scripts/run_scheduler_local_activation_suite.sh \
  --output-dir ./tmp/scheduler-local-activation-suite-report-<timestamp>
```

Expected artifacts:

```text
SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md
scheduler_local_activation_suite_report.json
suite_validation.json
01-dry-run-preflight/validation.json
02-audit-retention-activation/validation.json
03-eco-escalation-activation/validation.json
04-bom-to-mbom-activation/validation.json
```

## 5. Focused Tests

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_bom_to_mbom_activation_smoke_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

## 6. Boundary

- No scheduler runtime behavior change.
- No new task handler.
- No shared-dev 142 scheduler activation.
- No production scheduler activation.
- This is a local-dev evidence renderer only.
