# P2 Observation Regression Push And PR

Date: 2026-04-18

## Goal

Record the clean branch push and GitHub PR creation step for the P2 observation regression trigger/checklist and one-command wrapper changes.

## Branch

- Branch: `feature/p2-observation-regression-wrapper-20260418`
- Base branch: `main`

## Local commits pushed

The branch was pushed with these commits on top of `origin/main`:

1. `466aae0` `docs: add p2 observation regression trigger checklist`
2. `01721d8` `docs: add p2 observation regression wrapper`

## Push execution

Command:

```bash
git push -u origin feature/p2-observation-regression-wrapper-20260418
```

Observed:

- remote branch updated successfully
- local branch now tracks `origin/feature/p2-observation-regression-wrapper-20260418`

## PR creation

Created PR:

- PR: `<pending>`
- URL: `<pending>`
- Title: `docs: add p2 observation regression rerun workflow`

Base / head:

- base: `main`
- head: `feature/p2-observation-regression-wrapper-20260418`

## PR scope summary

This PR carries the P2 observation regression rerun closeout on top of the already merged observation baseline:

- trigger checklist for when reruns are required
- compare helper for baseline vs rerun result directories
- one-command wrapper for `verify + render + compare`
- one-page guide and runbook entry-point updates
- delivery doc index updates

## Verification snapshot used for push / PR

Verification commands:

```bash
bash -n scripts/run_p2_observation_regression.sh
scripts/run_p2_observation_regression.sh --help
```

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py
```

```bash
./local-dev-env/start.sh
BASE_URL=http://127.0.0.1:7910 \
TOKEN=<admin-jwt> \
TENANT_ID=tenant-1 \
ORG_ID=org-1 \
BASELINE_DIR=tmp/p2-observation-regression-20260418/baseline \
OUTPUT_DIR=tmp/p2-observation-regression-wrapper-smoke \
ENVIRONMENT=local-dev-wrapper \
OPERATOR=codex \
scripts/run_p2_observation_regression.sh
./local-dev-env/stop.sh
```

Result:

- wrapper shell syntax check passed
- wrapper help output passed
- delivery/runbook/doc-index contracts: `5 passed`
- local smoke produced:
  - `tmp/p2-observation-regression-wrapper-smoke/OBSERVATION_RESULT.md`
  - `tmp/p2-observation-regression-wrapper-smoke/OBSERVATION_DIFF.md`
- compare result remained stable against baseline:
  - `pending_count: 1 -> 1`
  - `overdue_count: 2 -> 2`
  - `escalated_count: 0 -> 0`
  - `total_anomalies: 2 -> 2`

## Main linked records

- `docs/DEV_AND_VERIFICATION_P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST_20260418.md`
- `docs/DEV_AND_VERIFICATION_P2_OBSERVATION_REGRESSION_ONE_COMMAND_20260418.md`
- `docs/P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST.md`
- `docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md`

## Limits

- This document records the push/PR step for the regression rerun helper layer, not a fresh shared-dev observation round
- The smoke validation here uses `local-dev-env`, not a shared-dev baseline
