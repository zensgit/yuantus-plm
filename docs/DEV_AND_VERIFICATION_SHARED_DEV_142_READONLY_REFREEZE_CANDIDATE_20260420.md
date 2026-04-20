# DEV_AND_VERIFICATION_SHARED_DEV_142_READONLY_REFREEZE_CANDIDATE_20260420

## Context

- Date: 2026-04-20
- Base branch: `main` at `2d24c0d5bbb51ea3cdef19c7bd60509909fa3de3`
- Goal: add a stable readonly candidate preview for `shared-dev 142` when `refreeze-readiness` blocks direct baseline refresh because of future-deadline pending approvals

## Change

Added a candidate-preview flow that:

1. reruns the current official readonly check
2. excludes future-deadline pending approvals from the current result
3. materializes a reviewable candidate artifact pack
4. leaves the tracked baseline untouched

New scripts:

- `scripts/run_p2_shared_dev_142_refreeze_candidate.sh`
- `scripts/render_p2_shared_dev_142_refreeze_candidate.py`
- `scripts/print_p2_shared_dev_142_refreeze_candidate_commands.sh`

New doc:

- `docs/P2_SHARED_DEV_142_READONLY_REFREEZE_CANDIDATE_CHECKLIST.md`

Selector / discoverability updates:

- `scripts/run_p2_shared_dev_142_entrypoint.sh`
  - new modes:
    - `refreeze-candidate`
    - `print-refreeze-candidate-commands`
- `README.md`
- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_SHARED_DEV_142_READONLY_REFREEZE_READINESS_CHECKLIST.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
- `docs/DELIVERY_DOC_INDEX.md`

## Behavior

The candidate helper writes:

- `current/*` from the nested readonly rerun
- `candidate/summary.json`
- `candidate/items.json`
- `candidate/anomalies.json`
- `candidate/export.json`
- `candidate/export.csv`
- `candidate/OBSERVATION_RESULT.md`
- `candidate/OBSERVATION_EVAL.md`
- top-level:
  - `STABLE_READONLY_CANDIDATE.md`
  - `stable_readonly_candidate.json`

Current design choice:

- exclude all non-overdue approvals from the candidate slice
- keep overdue and escalated rows intact
- do not rewrite the tracked frozen baseline automatically

## Local Verification

```bash
bash -n scripts/run_p2_shared_dev_142_refreeze_candidate.sh
bash -n scripts/print_p2_shared_dev_142_refreeze_candidate_commands.sh
python3 -m py_compile scripts/render_p2_shared_dev_142_refreeze_candidate.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py
```

## Real Shared-dev 142 Verification

Executed from the clean worktree:

```bash
bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode refreeze-candidate
```

Real runtime summary:

- `SUMMARY_HTTP_STATUS=200`
- `READONLY_EXIT_STATUS=0`
- `CANDIDATE_READY=1`
- `CANDIDATE_DECISION_KIND=overdue-only-stable-candidate`
- `EXCLUDED_PENDING_COUNT=1`

Real result directory:

- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529/`

Key artifacts:

- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529/current/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529/STABLE_READONLY_CANDIDATE.md`
- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529/stable_readonly_candidate.json`
- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529/candidate/OBSERVATION_RESULT.md`
- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529/candidate/OBSERVATION_EVAL.md`
- `tmp/p2-shared-dev-142-refreeze-candidate-20260420-234529.tar.gz`

Observed candidate decision:

- excluded pending approval:
  - `af1a2dc4-7d73-4d1d-aabb-acdde37abea8`
  - `eco-specialist`
  - `approval_deadline=2026-04-21T09:34:33.658929`
- current counts:
  - `items=5 / pending=1 / overdue=4 / escalated=1 / anomalies=3`
- candidate counts:
  - `items=4 / pending=0 / overdue=4 / escalated=1 / anomalies=3`

## Conclusion

This follow-up does not approve a new frozen baseline by itself.

It gives operators a concrete review pack for the alternate design:

- keep the live shared-dev environment unchanged
- evaluate a stable overdue-only candidate first
- decide baseline policy afterwards
