# DEV_AND_VERIFICATION_P2_OBSERVATION_WRAPPER_ENVFILE_ARCHIVE_20260419

## Objective

Reduce shared-dev observation execution friction after PR `#250` by extending the canonical wrapper:

- load defaults from a local env file
- auto-write a tarball archive for evidence handoff

This keeps the execution surface on the already-approved wrapper path instead of introducing another overlapping script.

## Scope

Changed:

- `scripts/run_p2_observation_regression.sh`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py`

No runtime API, approval-chain, dashboard, export, or audit behavior changed.

## Implementation

### 1. Wrapper execution surface

`scripts/run_p2_observation_regression.sh` now supports:

- `--env-file <path>`
- `--archive`
- env defaults via `ENV_FILE`
- auto archive control via `ARCHIVE_RESULT=1`
- archive path override via `ARCHIVE_PATH`

Design details:

- env file values only fill unset variables; explicit exported env still wins
- env file parsing is restricted to a fixed allowlist of wrapper-related keys
- archive defaults to a sibling tarball: `<OUTPUT_DIR>.tar.gz`

### 2. Operator docs

Updated the main operator-facing P2 docs to expose the same canonical path:

- one-page guide
- shared-dev handoff
- one-command regression note
- delivery scripts index

The result is one stable execution story:

1. keep secrets in a local env file
2. run the canonical wrapper
3. return the generated directory and tarball

## Verification

Executed:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Expected coverage from that set:

- wrapper behavior with `TOKEN`
- wrapper behavior with login fallback
- wrapper behavior with `--env-file` + `--archive`
- wrapper help contract for evaluator/entrypoint surface
- discoverability/index contracts
- shell syntax contract

## Outcome

Shared-dev observation no longer requires both of these manual steps every run:

- repeated `export BASE_URL/TOKEN/TENANT_ID/ORG_ID`
- manual `tar -czf ...` packaging

The canonical path remains the same script, but it now matches the actual handoff workflow more closely.
