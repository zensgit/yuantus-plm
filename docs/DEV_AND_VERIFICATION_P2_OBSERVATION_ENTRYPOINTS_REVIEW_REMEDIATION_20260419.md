# DEV AND VERIFICATION: P2 Observation Entrypoints Review Remediation (2026-04-19)

## Goal

Record the review-driven remediation applied on top of PR `#250` after the first publish of the P2 observation entrypoint convergence work.

This slice fixes:

1. `BASE_URL` trailing slash normalization in the workflow wrapper
2. misleading `--ref <branch-or-tag>` wording in the wrapper help
3. stale `ADMIN_TOKEN` references left behind in the remote observation runbook after the wrapper convergence rewrite

## Findings Addressed

### 1. Wrapper accepted trailing slash but forwarded it verbatim

File:

- `scripts/run_p2_observation_regression_workflow.sh`

Risk:

- operators could pass `https://host/`
- downstream tooling in this repo commonly normalizes trailing `/`
- keeping the raw value increases the chance of inconsistent URL handling

Fix:

- normalize early with:
  - `BASE_URL="${BASE_URL%/}"`

Verification:

- fake-`gh` wrapper test now passes `https://dev.example.invalid/`
- asserted dispatched field and summary JSON both store `https://dev.example.invalid`

### 2. Wrapper help overstated ref support

File:

- `scripts/run_p2_observation_regression_workflow.sh`

Risk:

- help said `--ref <branch-or-tag>`
- implementation discovers runs via `gh run list --branch "${REF}"`
- tag/commit refs are therefore not part of the current supported discovery path

Fix:

- narrow help text to:
  - `--ref <branch>`

This aligns the user-facing contract to the actual implementation instead of pretending tag support exists.

### 3. Remote runbook still contained broken old-token path

File:

- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`

Risk:

- baseline path had been converged to the wrapper
- later optional rerun / permission-check sections still referenced `ADMIN_TOKEN`
- the doc no longer created `ADMIN_TOKEN` before using it
- operator following the doc would hit an undefined-variable path

Fix:

- add an explicit `ADMIN_TOKEN` login snippet before the optional write-path checks
- switch the optional post-escalation reread step to:
  - `bash scripts/run_p2_observation_regression.sh`

That keeps the doc on the same canonical wrapper path and removes the stale split-brain between wrapper and raw verify/render.

## Contract Hardening

Updated:

- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`

Added coverage that the remote runbook still contains:

- `bash scripts/run_p2_observation_regression.sh`
- `ADMIN_TOKEN=$(`
- `TOKEN="$ADMIN_TOKEN"`
- `Authorization: Bearer $ADMIN_TOKEN`

This prevents the same partial rewrite from drifting back in later edits.

## Verification

### Commands

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

### Result

- `18 passed`

## Scope Boundary

This remediation does **not** change:

- workflow YAML
- observation APIs
- dashboard/export/audit semantics
- approval-chain behavior

It only fixes review findings in:

- wrapper ergonomics
- wrapper contract wording
- remote runbook correctness
- document contract coverage
