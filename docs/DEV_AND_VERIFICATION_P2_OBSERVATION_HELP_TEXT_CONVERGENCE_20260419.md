# DEV AND VERIFICATION: P2 Observation Help Text Convergence (2026-04-19)

## Goal

Close the last operator-facing drift left after `PR #253` by aligning the shell `--help` examples in the two canonical P2 observation scripts with the repo-safe shared-dev env-file guidance already documented elsewhere.

## Problem

After `#253` merged, the canonical docs and printed helper commands had already converged on:

- storing shared-dev env files under `$HOME/.config/yuantus/`
- avoiding repo-root credential files such as `./p2-shared-dev.env`

But the scripts themselves still advertised:

- `scripts/precheck_p2_observation_regression.sh --env-file ./p2-shared-dev.env`
- `scripts/run_p2_observation_regression.sh --env-file ./p2-shared-dev.env`

That meant the operator-facing help text was still one step behind the docs.

## Implementation

Updated:

- `scripts/precheck_p2_observation_regression.sh`
- `scripts/run_p2_observation_regression.sh`

Both `Usage:` examples now point to:

- `$HOME/.config/yuantus/p2-shared-dev.env`

Added a focused shell-help contract in:

- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

The contract verifies that both scripts:

- render help successfully
- include the repo-safe env-file location
- do not regress back to `./p2-shared-dev.env`

## Verification

Executed:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## Outcome

The P2 observation operator surface is now consistent across:

- canonical docs
- printed helper commands
- direct script `--help` output

No runtime logic or wrapper behavior changed.
