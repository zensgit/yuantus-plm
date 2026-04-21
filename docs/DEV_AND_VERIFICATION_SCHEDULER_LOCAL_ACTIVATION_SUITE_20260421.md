# DEV / Verification - Scheduler Local Activation Suite - 2026-04-21

## 1. Goal

Provide a single local-dev command that chains the three scheduler activation confidence checks already delivered separately:

1. dry-run preflight,
2. audit-retention activation,
3. ECO escalation activation.

This is an evidence-pack wrapper, not a new scheduler runtime feature.

## 2. Delivered

- `scripts/run_scheduler_local_activation_suite.sh`
- `src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py`
- CI contracts wiring in `.github/workflows/ci.yml`
- Script syntax wiring in `test_ci_shell_scripts_syntax.py`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Script Behavior

The helper is local-dev only and writes one parent evidence directory:

- `01-dry-run-preflight`
- `02-audit-retention-activation`
- `03-eco-escalation-activation`
- `suite_validation.json`
- `SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md`
- `scheduler_local_activation_suite_report.json`
- `README.txt`

It delegates to:

- `scripts/run_scheduler_dry_run_preflight.sh`
- `scripts/run_scheduler_audit_retention_activation_smoke.sh`
- `scripts/run_scheduler_eco_escalation_activation_smoke.sh`

## 4. Safety Boundary

- Refuses non-SQLite DB URLs.
- Refuses SQLite DBs outside `local-dev-env/data`.
- Local-dev only.
- Not for shared-dev or production.
- The two activation steps are intentionally destructive inside local-dev SQLite.

## 5. Suite Validation

`suite_validation.json` requires all three child `validation.json` files to report `ok: true`:

- `dry_run_preflight`,
- `audit_retention_activation`,
- `eco_escalation_activation`.

## 6. Verification

Focused contract command:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_contracts.py \
  src/yuantus/meta_engine/tests/test_scheduler_local_activation_suite_report_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Runtime smoke command:

```bash
bash scripts/run_scheduler_local_activation_suite.sh \
  --output-dir ./tmp/scheduler-local-activation-suite-<timestamp>
```

Prerequisite: `local-dev-env/start.sh` must have created `local-dev-env/data/yuantus.db`.

## 7. Non-Goals

- No scheduler runtime behavior changes.
- No shared-dev 142 scheduler activation.
- No production scheduler enablement.
- No additional scheduler task type.
