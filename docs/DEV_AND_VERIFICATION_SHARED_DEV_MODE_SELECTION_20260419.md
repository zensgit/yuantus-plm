# DEV AND VERIFICATION: Shared-dev Mode Selection (2026-04-19)

## Goal

Close the operator decision gap between the two already-existing shared-dev entry paths:

- existing shared-dev rerun
- fresh or explicitly resettable shared-dev first-run bootstrap

Without this gate, an operator can still land on bootstrap material first and make a bad choice on an in-use environment.

## Problem

The repo already contained:

- `scripts/print_p2_shared_dev_observation_commands.sh`
- `scripts/print_p2_shared_dev_first_run_commands.sh`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md`

But it did not yet expose a single first decision point that says:

- unknown resetability -> rerun path
- explicit reset approval -> first-run path

That ambiguity is especially risky for long-lived shared-dev hosts.

## Implementation

Added:

- `scripts/print_p2_shared_dev_mode_selection.sh`

Updated:

- `scripts/print_p2_shared_dev_observation_commands.sh`
- `scripts/print_p2_shared_dev_first_run_commands.sh`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`
- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

## Decision Rule Now Fixed

The operator-facing rule is now:

- if reset permission is unknown, use existing shared-dev rerun
- only use bootstrap after explicit confirmation the environment may be reset and fixtures may be initialized

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

Shared-dev now has three clear operator layers:

1. mode selection
2. existing shared-dev rerun
3. fresh/resettable shared-dev first-run

That closes the last decision ambiguity before real shared-dev execution.
