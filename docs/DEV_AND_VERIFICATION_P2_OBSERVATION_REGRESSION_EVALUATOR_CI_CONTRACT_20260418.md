# DEV AND VERIFICATION - P2 Observation Regression Evaluator CI Contract - 2026-04-18

## Goal

Move the P2 observation evaluator from a runbook-only capability into a fixed CI contract surface.

## Delivered

- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py`
- `.github/workflows/ci.yml`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

## What Changed

### 1. Dedicated CI contract for evaluator wiring

Added a focused contract test that locks four things:

- `scripts/run_p2_observation_regression.sh` exists and passes `bash -n`
- `scripts/evaluate_p2_observation_results.py` exists and passes `py_compile`
- wrapper `--help` still exposes `EVAL_MODE / EXPECT_DELTAS / EVAL_OUTPUT`
- the main P2 regression docs still point to the wrapper/evaluator entrypoints

### 2. CI workflow wiring

Added the new contract test to the `Contract checks (perf workflows + delivery doc index)` step in `.github/workflows/ci.yml`.

This matters because `test_ci_contracts_job_wiring.py` only proves coverage when the workflow actually executes the file.

### 3. Shell syntax guard

Added `scripts/run_p2_observation_regression.sh` to `test_ci_shell_scripts_syntax.py` so the wrapper is covered by the shared shell-syntax contract layer, not only by the new dedicated test.

## Verification

### 1. Focused contract tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py
```

Observed:

- `13 passed`

### 2. Docs index contracts

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

## Outcome

The evaluator path now has a fixed CI entrypoint:

1. script syntax stays guarded
2. wrapper help contract stays guarded
3. docs-to-entrypoint references stay guarded
4. workflow wiring stays guarded

That is the right boundary for this stage. It prevents silent drift without forcing live environment access inside CI.
