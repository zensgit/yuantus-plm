# DEV AND VERIFICATION - P2 Observation Regression One-Command Run - 2026-04-18

## Goal

Add a single wrapper command for the common P2 regression path so operators no longer have to manually chain verify, render, and compare.

## Delivered

- `scripts/run_p2_observation_regression.sh`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`

## Behavior

The wrapper:

1. runs `scripts/verify_p2_dev_observation_startup.sh`
2. runs `scripts/render_p2_observation_result.py`
3. optionally runs `scripts/compare_p2_observation_results.py` when `BASELINE_DIR` is set
4. optionally runs `scripts/evaluate_p2_observation_results.py` when `EVAL_MODE` is set

## Verification

```bash
bash -n scripts/run_p2_observation_regression.sh
scripts/run_p2_observation_regression.sh --help
```

Result:

- `bash -n` passed
- `--help` output verified required and optional env contract

If a live local regression environment is available, a recommended smoke is:

```bash
BASE_URL=http://127.0.0.1:7910 \
TOKEN=<jwt> \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
BASELINE_DIR=tmp/p2-observation-regression-20260418/baseline \
OUTPUT_DIR=tmp/p2-observation-regression-wrapper-smoke \
scripts/run_p2_observation_regression.sh
```

Executed local smoke:

```bash
./local-dev-env/start.sh
ADMIN_TOKEN=$(curl -sS -X POST http://127.0.0.1:7910/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"tenant-1","org_id":"org-1","username":"admin","password":"admin"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

BASE_URL=http://127.0.0.1:7910 \
TOKEN="$ADMIN_TOKEN" \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
BASELINE_DIR=tmp/p2-observation-regression-20260418/baseline \
OUTPUT_DIR=tmp/p2-observation-regression-wrapper-smoke \
ENVIRONMENT=local-dev-wrapper \
OPERATOR=codex \
scripts/run_p2_observation_regression.sh

./local-dev-env/stop.sh
```

Smoke result:

- verify script returned `5 x 200`
- rendered `tmp/p2-observation-regression-wrapper-smoke/OBSERVATION_RESULT.md`
- rendered `tmp/p2-observation-regression-wrapper-smoke/OBSERVATION_DIFF.md`
- compare result stayed stable against baseline:
  - `pending_count: 1 -> 1`
  - `overdue_count: 2 -> 2`
  - `escalated_count: 0 -> 0`
  - `total_anomalies: 2 -> 2`
  - `items/export-json/export-csv`: all `3 -> 3`

Docs contracts:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Result:

- `5 passed`
