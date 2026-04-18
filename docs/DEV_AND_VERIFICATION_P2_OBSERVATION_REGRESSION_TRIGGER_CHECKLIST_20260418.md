# DEV AND VERIFICATION - P2 Observation Regression Trigger Checklist - 2026-04-18

## Goal

Define a minimal, repeatable trigger rule for rerunning P2 observation regression after later changes.

## Delivered

- `docs/P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST.md`
- `scripts/compare_p2_observation_results.py`

## Intent

The checklist narrows reruns to four classes:

- runtime observation-surface changes
- observation tooling changes
- data/seed/auth changes that alter semantics
- replay/remediation changes that touch ECO approval paths

It also separates:

- read-only reruns
- state-transition reruns
- permission tri-state reruns

## Verification

```bash
python3 scripts/compare_p2_observation_results.py \
  tmp/p2-observation-regression-20260418/baseline \
  tmp/p2-observation-regression-20260418/after-escalate \
  --baseline-label baseline \
  --current-label after-escalate
```

Expected:

- exits `0`
- creates `tmp/p2-observation-regression-20260418/after-escalate/OBSERVATION_DIFF.md`
- diff shows:
  - `overdue_count: 2 -> 3`
  - `escalated_count: 0 -> 1`
  - `overdue_not_escalated: 2 -> 1`
  - `escalated_unresolved: 0 -> 1`

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
