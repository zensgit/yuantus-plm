# DEV_AND_VERIFICATION_P2_OBSERVATION_LOCAL_PRECHECK_20260419

## Objective

Fill the last shell-side execution gap before real shared-dev observation by adding a cheap local precheck step that validates:

- auth input readiness
- base URL reachability
- dashboard summary read-surface accessibility

without forcing operators to launch the full observation collection first.

## Scope

Added:

- `scripts/precheck_p2_observation_regression.sh`

Updated:

- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py`

No runtime API or workflow semantics changed.

## Implementation

### 1. Local precheck shell entrypoint

`scripts/precheck_p2_observation_regression.sh` supports:

- direct `TOKEN` auth
- `USERNAME/PASSWORD` login fallback
- local env defaults via `--env-file` / `ENV_FILE`
- optional tenant/org headers
- optional summary filters

It writes three artifacts under `OUTPUT_DIR`:

- `OBSERVATION_PRECHECK.md`
- `observation_precheck.json`
- `summary_probe.json`

### 2. Failure behavior

The script preserves local evidence on failure, similar to the workflow-side precheck pattern:

- missing auth env
- failed login
- missing `access_token`
- summary probe HTTP failure

### 3. Operator flow convergence

The canonical shell flow is now:

1. run local precheck
2. if green, run `run_p2_observation_regression.sh`
3. archive and return results

That reduces wasted full runs when shared-dev creds or headers are wrong.

## Verification

Executed:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Coverage from that set:

- precheck login success
- precheck env-file success
- precheck unauthorized summary failure with preserved evidence
- shell syntax/help contract
- doc/index/discoverability contract

## Outcome

Local shell execution now has the same staged shape as the workflow path:

- precheck first
- then full observation

This is the right place to stop before real shared-dev credentials are available.
