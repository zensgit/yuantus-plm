# DEV AND VERIFICATION: P2 Observation Shared-Dev Execution Gate Review Remediation (2026-04-19)

## Goal

Record the review-driven remediation applied on top of PR `#253` after bot review surfaced two real operator-facing issues in the shared-dev credential handoff examples:

- env-file examples mixed `ARCHIVE_RESULT=1` into the same file consumed by `scripts/precheck_p2_observation_regression.sh`
- examples wrote real shared-dev credentials to a repo-root env file path

## Findings

### 1. Precheck compatibility drift

`scripts/precheck_p2_observation_regression.sh --env-file ...` only accepts a fixed whitelist of keys and does **not** allow `ARCHIVE_RESULT`.

Several canonical docs and the printed helper command still showed:

- one shared env file
- that same env file passed to precheck
- `ARCHIVE_RESULT=1` placed inside the file

That operator flow was wrong.

### 2. Credential placement risk

Several docs still showed writing live shared-dev credentials to:

- `./p2-shared-dev.env`
- `./p2-observation.env`

Those repo-root examples created unnecessary accidental-commit risk.

## Remediation

Updated the canonical operator-facing surfaces so they now converge on:

- storing shared-dev env files outside the repo under `$HOME/.config/yuantus/`
- keeping env-file contents precheck-compatible
- enabling archive behavior only on the regression wrapper command line

## Files Changed

- `docs/DEV_AND_VERIFICATION_P2_OBSERVATION_SHARED_DEV_EXECUTION_GATE_20260419.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`

## Contract Added

Added a focused discoverability/usage contract that now enforces:

- shared-dev env-file examples stay outside repo root
- repo-root `./p2-shared-dev.env` and `./p2-observation.env` examples do not reappear
- `ARCHIVE_RESULT=1` stays out of `ENVEOF` blocks
- archive enablement still remains documented on the wrapper path

## Verification

Executed:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

- `17 passed`

## Outcome

PR `#253` no longer carries misleading shared-dev handoff examples.

The canonical operator path is now consistent:

1. store credentials outside the repo
2. run precheck with a precheck-compatible env file
3. enable archive only when running the regression wrapper
