# DEV AND VERIFICATION - P2 Observation Regression Evaluation - 2026-04-18

## Goal

Add an executable evaluation layer for P2 observation regression so operators no longer have to rely only on manual diff reading.

## Delivered

- `scripts/evaluate_p2_observation_results.py`
- `docs/P2_OBSERVATION_REGRESSION_EVALUATION.md`
- wrapper extension in `scripts/run_p2_observation_regression.sh`

## Scope

The evaluator adds three modes:

1. `current-only`
2. `readonly`
3. `state-change`

It intentionally stays on artifact-level contracts:

- `summary.json`
- `items.json`
- `export.json`
- `export.csv`
- `anomalies.json`

It does not compare volatile fields such as `hours_overdue` or deep bucket payload details.

## Checks Implemented

All modes enforce:

- `items.json / export.json / export.csv` row-count consistency
- `summary.pending_count / overdue_count / escalated_count` matches `items.json` derivation
- `anomalies.total_anomalies` matches anomaly bucket totals

`readonly` additionally enforces:

- core metrics equal to baseline

`state-change` additionally enforces:

- user-declared metric deltas

## Verification

### 1. CLI tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_evaluation_script.py
```

Observed:

- `4 passed`

### 2. Docs contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

Observed:

- `5 passed`

### 3. Existing baseline readonly evaluation

```bash
python3 scripts/evaluate_p2_observation_results.py \
  tmp/p2-observation-regression-wrapper-smoke \
  --mode readonly \
  --baseline-dir tmp/p2-observation-regression-20260418/baseline
```

Observed:

- exit `0`
- created `tmp/p2-observation-regression-wrapper-smoke/OBSERVATION_EVAL.md`
- verdict `PASS`
- `20/20` checks passed

### 4. Existing state-change evaluation

```bash
python3 scripts/evaluate_p2_observation_results.py \
  tmp/p2-observation-regression-20260418/after-escalate \
  --mode state-change \
  --baseline-dir tmp/p2-observation-regression-20260418/baseline \
  --expect-delta overdue_count=1 \
  --expect-delta escalated_count=1 \
  --expect-delta items_count=1 \
  --expect-delta export_json_count=1 \
  --expect-delta export_csv_rows=1 \
  --expect-delta escalated_unresolved=1 \
  --expect-delta overdue_not_escalated=-1
```

Observed:

- exit `0`
- created `tmp/p2-observation-regression-20260418/after-escalate/OBSERVATION_EVAL.md`
- verdict `PASS`
- `17/17` checks passed

### 5. Wrapper help and syntax

```bash
bash -n scripts/run_p2_observation_regression.sh
scripts/run_p2_observation_regression.sh --help
```

Observed:

- syntax check passed
- help output contains `EVAL_MODE`, `EXPECT_DELTAS`, `EVAL_OUTPUT`

### 6. Wrapper smoke with evaluator enabled

```bash
./local-dev-env/start.sh
BASE_URL=http://127.0.0.1:7910 \
TOKEN=<admin-jwt> \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
BASELINE_DIR=tmp/p2-observation-regression-20260418/baseline \
OUTPUT_DIR=tmp/p2-observation-regression-eval-wrapper-smoke \
ENVIRONMENT=local-dev-eval-wrapper \
OPERATOR=codex \
EVAL_MODE=readonly \
scripts/run_p2_observation_regression.sh
./local-dev-env/stop.sh
```

Observed:

- wrapper emitted:
  - `OBSERVATION_RESULT.md`
  - `OBSERVATION_DIFF.md`
  - `OBSERVATION_EVAL.md`
- readonly evaluation verdict `PASS`
- `20/20` checks passed

## Outcome

P2 observation regression now has four layers:

1. collect
2. render
3. compare
4. evaluate

This closes the gap between “human-readable evidence” and “machine-checkable verdict”.

## Limits

- Permission `401 / 403 / 200` checks remain a separate smoke branch
- `state-change` mode only evaluates declared deltas; it does not infer business intent automatically
